from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import PhysicalUnit, Placement, PlacementZone
from .services import move_unit


class RelativePosition:
    LEFTMOST = "LEFTMOST"
    RIGHTMOST = "RIGHTMOST"
    BEFORE = "BEFORE"
    AFTER = "AFTER"


@transaction.atomic
def move_unit_relative(
    *,
    unit: PhysicalUnit,
    zone: PlacementZone | None = None,
    support_unit: PhysicalUnit | None = None,
    position: str = RelativePosition.RIGHTMOST,
    reference_unit: PhysicalUnit | None = None,
    actor=None,
    note: str = "",
):
    """Move/reorder a unit using human-relative placement rather than raw order keys."""

    if (zone is None) == (support_unit is None):
        raise ValidationError("Specify exactly one of zone or support_unit.")
    if position not in {
        RelativePosition.LEFTMOST,
        RelativePosition.RIGHTMOST,
        RelativePosition.BEFORE,
        RelativePosition.AFTER,
    }:
        raise ValidationError({"position": "Unsupported relative position."})

    if zone is not None:
        siblings = list(
            Placement.objects.filter(zone=zone)
            .exclude(unit=unit)
            .select_related("unit")
            .order_by("order_key", "unit__code")
        )
    else:
        siblings = list(
            Placement.objects.filter(support_unit=support_unit)
            .exclude(unit=unit)
            .select_related("unit")
            .order_by("order_key", "unit__code")
        )

    sibling_ids = [placement.unit_id for placement in siblings]
    if position in {RelativePosition.BEFORE, RelativePosition.AFTER}:
        if reference_unit is None or reference_unit.pk not in sibling_ids:
            raise ValidationError(
                {"reference_unit": "基準にする物は、選択した配置先に既にある物を選んでください。"}
            )
        reference_index = sibling_ids.index(reference_unit.pk)
        insert_index = reference_index if position == RelativePosition.BEFORE else reference_index + 1
    elif position == RelativePosition.LEFTMOST:
        insert_index = 0
    else:
        insert_index = len(siblings)

    sequence: list[PhysicalUnit] = [placement.unit for placement in siblings]
    sequence.insert(insert_index, unit)

    now = timezone.now()
    target_order = 100
    for index, sequence_unit in enumerate(sequence, start=1):
        order_key = index * 100
        if sequence_unit.pk == unit.pk:
            target_order = order_key
            continue
        Placement.objects.filter(unit=sequence_unit).update(order_key=order_key, updated_at=now)

    return move_unit(
        unit=unit,
        zone=zone,
        support_unit=support_unit,
        order_key=target_order,
        actor=actor,
        note=note,
    )
