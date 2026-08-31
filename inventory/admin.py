from django.contrib import admin

from .models import (
    CatalogItem,
    Fixture,
    PhysicalUnit,
    Placement,
    PlacementChange,
    PlacementZone,
    Room,
    Stock,
    StockChange,
)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "room", "is_active")
    search_fields = ("code", "name", "room__code", "room__name")
    list_filter = ("kind", "is_active", "room")


@admin.register(PlacementZone)
class PlacementZoneAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "fixture", "level_order", "is_active")
    search_fields = ("code", "name", "fixture__code", "fixture__name")
    list_filter = ("kind", "is_active", "fixture")


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "tracking_mode", "unit", "is_active")
    search_fields = ("code", "name", "manufacturer", "part_number")
    list_filter = ("tracking_mode", "category", "is_active")


@admin.register(PhysicalUnit)
class PhysicalUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "catalog_item", "is_active")
    search_fields = ("code", "name", "catalog_item__code", "catalog_item__name")
    list_filter = ("kind", "is_active")


class OperationalReadOnlyAdmin(admin.ModelAdmin):
    """Keep operational mutations on audited application service paths."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Placement)
class PlacementAdmin(OperationalReadOnlyAdmin):
    list_display = ("unit", "zone", "support_unit", "order_key", "updated_at")
    search_fields = ("unit__code", "unit__name", "zone__code", "support_unit__code")
    list_filter = ("zone__fixture",)


@admin.register(Stock)
class StockAdmin(OperationalReadOnlyAdmin):
    list_display = ("item", "holder", "quantity", "updated_at")
    search_fields = ("item__code", "item__name", "holder__code", "holder__name")


@admin.register(StockChange)
class StockChangeAdmin(OperationalReadOnlyAdmin):
    list_display = ("stock", "delta", "resulting_quantity", "reason", "actor", "created_at")
    search_fields = ("stock__item__code", "stock__holder__code", "note")
    list_filter = ("reason", "created_at")


@admin.register(PlacementChange)
class PlacementChangeAdmin(OperationalReadOnlyAdmin):
    list_display = ("unit", "from_zone", "from_support_unit", "to_zone", "to_support_unit", "actor", "created_at")
    search_fields = ("unit__code", "unit__name", "note")
    list_filter = ("created_at",)
