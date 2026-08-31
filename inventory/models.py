from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class DimensionedModel(models.Model):
    width_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    depth_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        abstract = True


class Room(DimensionedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Fixture(DimensionedModel):
    class Kind(models.TextChoices):
        RACK = "RACK", "ラック"
        DESK = "DESK", "机"
        WALL = "WALL", "壁面"
        CABINET = "CABINET", "キャビネット"
        WORKBENCH = "WORKBENCH", "作業台"
        OTHER = "OTHER", "その他"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="fixtures")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    x_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    y_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    z_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rotation_z_deg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["room__code", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class PlacementZone(DimensionedModel):
    class Kind(models.TextChoices):
        VOLUME = "VOLUME", "収納空間"
        SURFACE = "SURFACE", "設置面"
        WALL = "WALL", "壁面領域"
        ANCHOR = "ANCHOR", "固定点"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    fixture = models.ForeignKey(Fixture, on_delete=models.PROTECT, related_name="zones")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    level_order = models.PositiveIntegerField(null=True, blank=True)
    x_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    y_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    z_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["fixture__code", "level_order", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class CatalogItem(models.Model):
    class TrackingMode(models.TextChoices):
        QUANTITY = "QUANTITY", "数量管理"
        INDIVIDUAL = "INDIVIDUAL", "個体管理"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=80, blank=True)
    tracking_mode = models.CharField(max_length=16, choices=TrackingMode.choices)
    unit = models.CharField(max_length=24, blank=True)
    minimum_stock = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    part_number = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class PhysicalUnit(DimensionedModel):
    class Kind(models.TextChoices):
        CONTAINER = "CONTAINER", "収納容器"
        CARTON = "CARTON", "段ボール等"
        EQUIPMENT = "EQUIPMENT", "機器"
        TOOL = "TOOL", "工具"
        OTHER = "OTHER", "その他"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.PROTECT,
        related_name="physical_units",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Placement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(PhysicalUnit, on_delete=models.CASCADE, related_name="placement")
    zone = models.ForeignKey(
        PlacementZone,
        on_delete=models.PROTECT,
        related_name="placements",
        null=True,
        blank=True,
    )
    support_unit = models.ForeignKey(
        PhysicalUnit,
        on_delete=models.PROTECT,
        related_name="supported_placements",
        null=True,
        blank=True,
    )
    order_key = models.PositiveIntegerField(default=100)
    offset_x_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offset_y_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offset_z_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rotation_z_deg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_key", "unit__code"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(zone__isnull=False, support_unit__isnull=True)
                    | Q(zone__isnull=True, support_unit__isnull=False)
                ),
                name="placement_exactly_one_parent",
            ),
            models.CheckConstraint(
                condition=~Q(unit=F("support_unit")),
                name="placement_no_self_support",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if not self.unit_id or not self.support_unit_id:
            return
        if self.unit_id == self.support_unit_id:
            raise ValidationError({"support_unit": "A physical unit cannot support itself."})

        current_id = self.support_unit_id
        visited: set[uuid.UUID] = set()
        while current_id:
            if current_id == self.unit_id:
                raise ValidationError({"support_unit": "This placement would create a support cycle."})
            if current_id in visited:
                raise ValidationError({"support_unit": "The existing support chain already contains a cycle."})
            visited.add(current_id)
            current_id = (
                Placement.objects.filter(unit_id=current_id)
                .values_list("support_unit_id", flat=True)
                .first()
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.zone_id:
            return f"{self.unit.code} → {self.zone.code}"
        return f"{self.unit.code} → on {self.support_unit.code}"


class Stock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, related_name="stocks")
    holder = models.ForeignKey(PhysicalUnit, on_delete=models.PROTECT, related_name="stocks")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item__code", "holder__code"]
        constraints = [
            models.UniqueConstraint(fields=["item", "holder"], name="stock_unique_item_holder"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_quantity_nonnegative"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.item_id and self.item.tracking_mode != CatalogItem.TrackingMode.QUANTITY:
            raise ValidationError({"item": "Stock rows require a quantity-tracked catalog item."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.item.code} @ {self.holder.code}: {self.quantity} {self.item.unit}".strip()


class StockChange(models.Model):
    class Reason(models.TextChoices):
        PURCHASE = "PURCHASE", "購入・入庫"
        USE = "USE", "使用・出庫"
        COUNT = "COUNT", "棚卸補正"
        TRANSFER = "TRANSFER", "移し替え"
        OTHER = "OTHER", "その他"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name="changes")
    delta = models.DecimalField(max_digits=14, decimal_places=3)
    resulting_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.CharField(max_length=16, choices=Reason.choices)
    note = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_stock_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(resulting_quantity__gte=0),
                name="stock_change_result_nonnegative",
            )
        ]


class PlacementChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(PhysicalUnit, on_delete=models.PROTECT, related_name="placement_changes")
    from_zone = models.ForeignKey(
        PlacementZone,
        on_delete=models.PROTECT,
        related_name="placement_changes_from",
        null=True,
        blank=True,
    )
    from_support_unit = models.ForeignKey(
        PhysicalUnit,
        on_delete=models.PROTECT,
        related_name="placement_changes_supported_from",
        null=True,
        blank=True,
    )
    to_zone = models.ForeignKey(
        PlacementZone,
        on_delete=models.PROTECT,
        related_name="placement_changes_to",
        null=True,
        blank=True,
    )
    to_support_unit = models.ForeignKey(
        PhysicalUnit,
        on_delete=models.PROTECT,
        related_name="placement_changes_supported_to",
        null=True,
        blank=True,
    )
    from_order_key = models.PositiveIntegerField(null=True, blank=True)
    to_order_key = models.PositiveIntegerField(default=100)
    note = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_placement_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
