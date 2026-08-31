from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    CatalogItem,
    PhysicalUnit,
    Placement,
    PlacementChange,
    PlacementZone,
    Stock,
    StockChange,
)


class StockUnderflowError(ValidationError):
    pass


def _decimal(value: Decimal | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


@transaction.atomic
def create_stock(
    *,
    item: CatalogItem,
    holder: PhysicalUnit,
    initial_quantity: Decimal | int | str = 0,
    reason: str = StockChange.Reason.COUNT,
    actor=None,
    note: str = "",
) -> tuple[Stock, StockChange]:
    """Create a quantity-tracked stock row and its initial audit record atomically."""

    quantity = _decimal(initial_quantity)
    if item.tracking_mode != CatalogItem.TrackingMode.QUANTITY:
        raise ValidationError({"item": "Only quantity-tracked items can create stock rows."})
    if quantity < 0:
        raise ValidationError({"initial_quantity": "Initial quantity cannot be negative."})

    stock = Stock.objects.create(item=item, holder=holder, quantity=quantity)
    change = StockChange.objects.create(
        stock=stock,
        delta=quantity,
        resulting_quantity=quantity,
        reason=reason,
        note=note,
        actor=actor,
    )
    return stock, change


@transaction.atomic
def adjust_stock(
    *,
    stock: Stock,
    delta: Decimal | int | str,
    reason: str,
    actor=None,
    note: str = "",
) -> StockChange:
    """Apply a relative stock change and create its audit record atomically."""

    delta_value = _decimal(delta)
    now = timezone.now()

    queryset = Stock.objects.filter(pk=stock.pk)
    if delta_value < 0:
        queryset = queryset.filter(quantity__gte=-delta_value)

    updated = queryset.update(
        quantity=F("quantity") + delta_value,
        updated_at=now,
    )
    if updated != 1:
        if not Stock.objects.filter(pk=stock.pk).exists():
            raise Stock.DoesNotExist(f"Stock row does not exist: {stock.pk}")
        raise StockUnderflowError("Stock quantity cannot become negative.")

    current = Stock.objects.get(pk=stock.pk)
    return StockChange.objects.create(
        stock=current,
        delta=delta_value,
        resulting_quantity=current.quantity,
        reason=reason,
        note=note,
        actor=actor,
    )


@transaction.atomic
def reconcile_stock(
    *,
    stock: Stock,
    counted_quantity: Decimal | int | str,
    actor=None,
    note: str = "",
) -> StockChange:
    """Set a counted absolute quantity while preserving the correction delta."""

    counted = _decimal(counted_quantity)
    if counted < 0:
        raise ValidationError({"counted_quantity": "Counted quantity cannot be negative."})

    current = Stock.objects.get(pk=stock.pk)
    delta = counted - current.quantity
    Stock.objects.filter(pk=current.pk).update(quantity=counted, updated_at=timezone.now())
    current.refresh_from_db(fields=["quantity", "updated_at"])

    return StockChange.objects.create(
        stock=current,
        delta=delta,
        resulting_quantity=current.quantity,
        reason=StockChange.Reason.COUNT,
        note=note,
        actor=actor,
    )


@transaction.atomic
def move_unit(
    *,
    unit: PhysicalUnit,
    zone: PlacementZone | None = None,
    support_unit: PhysicalUnit | None = None,
    order_key: int = 100,
    actor=None,
    note: str = "",
) -> tuple[Placement, PlacementChange | None]:
    """Move a unit to a zone or onto another unit and audit a real change."""

    if (zone is None) == (support_unit is None):
        raise ValidationError("Specify exactly one of zone or support_unit.")
    if order_key < 0:
        raise ValidationError({"order_key": "Order key cannot be negative."})

    try:
        placement = Placement.objects.get(unit=unit)
        from_zone = placement.zone
        from_support = placement.support_unit
        from_order = placement.order_key
    except Placement.DoesNotExist:
        placement = Placement(unit=unit)
        from_zone = None
        from_support = None
        from_order = None

    is_noop = (
        placement.pk is not None
        and placement.zone_id == (zone.pk if zone else None)
        and placement.support_unit_id == (support_unit.pk if support_unit else None)
        and placement.order_key == order_key
    )
    if is_noop:
        return placement, None

    placement.zone = zone
    placement.support_unit = support_unit
    placement.order_key = order_key
    placement.save()

    change = PlacementChange.objects.create(
        unit=unit,
        from_zone=from_zone,
        from_support_unit=from_support,
        to_zone=zone,
        to_support_unit=support_unit,
        from_order_key=from_order,
        to_order_key=order_key,
        note=note,
        actor=actor,
    )
    return placement, change


def resolve_effective_zone(unit: PhysicalUnit) -> PlacementZone | None:
    """Resolve current effective zone from authoritative DB rows, ignoring stale ORM relation caches."""

    current_id = unit.pk
    visited: set[object] = set()
    while current_id:
        if current_id in visited:
            raise ValidationError("Support cycle detected while resolving effective zone.")
        visited.add(current_id)

        row = (
            Placement.objects.filter(unit_id=current_id)
            .values("zone_id", "support_unit_id")
            .first()
        )
        if row is None:
            return None
        if row["zone_id"]:
            return PlacementZone.objects.get(pk=row["zone_id"])
        current_id = row["support_unit_id"]

    return None
