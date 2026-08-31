from __future__ import annotations

from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce

from .models import CatalogItem


STOCK_TOTAL_FIELD = DecimalField(max_digits=14, decimal_places=3)


def quantity_items_with_totals():
    """Return active quantity-tracked items annotated with their current total stock."""

    return CatalogItem.objects.filter(
        is_active=True,
        tracking_mode=CatalogItem.TrackingMode.QUANTITY,
    ).annotate(
        total_stock=Coalesce(
            Sum("stocks__quantity"),
            Value(Decimal("0")),
            output_field=STOCK_TOTAL_FIELD,
        )
    )


def low_stock_items():
    """Return threshold-configured items whose aggregate stock is below the threshold."""

    return (
        quantity_items_with_totals()
        .filter(
            minimum_stock__isnull=False,
            total_stock__lt=F("minimum_stock"),
        )
        .annotate(
            shortage=ExpressionWrapper(
                F("minimum_stock") - F("total_stock"),
                output_field=STOCK_TOTAL_FIELD,
            )
        )
        .order_by("total_stock", "code")
    )
