from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from inventory.models import (
    CatalogItem,
    Fixture,
    PhysicalUnit,
    PlacementChange,
    PlacementZone,
    Room,
    Stock,
    StockChange,
)
from inventory.services import (
    StockUnderflowError,
    adjust_stock,
    move_unit,
    reconcile_stock,
    resolve_effective_zone,
)


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(code="ROOM-A", name="Main lab")
        self.rack = Fixture.objects.create(
            code="R-001",
            name="Rack 1",
            room=self.room,
            kind=Fixture.Kind.RACK,
        )
        self.zone1 = PlacementZone.objects.create(
            code="Z-001",
            name="Shelf 1",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=1,
        )
        self.zone2 = PlacementZone.objects.create(
            code="Z-002",
            name="Shelf 2",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=2,
        )
        self.item = CatalogItem.objects.create(
            code="I-001",
            name="M3 bolt",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
        )
        self.unit_a = PhysicalUnit.objects.create(
            code="C-001", name="Box A", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.unit_b = PhysicalUnit.objects.create(
            code="C-002", name="Box B", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.unit_c = PhysicalUnit.objects.create(
            code="C-003", name="Box C", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.stock = Stock.objects.create(item=self.item, holder=self.unit_a, quantity=10)

    def test_adjust_stock_updates_quantity_and_audit_together(self):
        change = adjust_stock(
            stock=self.stock,
            delta=-3,
            reason=StockChange.Reason.USE,
            note="prototype",
        )
        self.stock.refresh_from_db()

        self.assertEqual(self.stock.quantity, Decimal("7.000"))
        self.assertEqual(change.delta, Decimal("-3"))
        self.assertEqual(change.resulting_quantity, Decimal("7.000"))
        self.assertEqual(StockChange.objects.count(), 1)

    def test_adjust_stock_rejects_underflow_without_partial_audit(self):
        with self.assertRaises(StockUnderflowError):
            adjust_stock(
                stock=self.stock,
                delta=-11,
                reason=StockChange.Reason.USE,
            )

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("10.000"))
        self.assertEqual(StockChange.objects.count(), 0)

    def test_reconcile_stock_records_difference(self):
        change = reconcile_stock(stock=self.stock, counted_quantity=8, note="count")
        self.stock.refresh_from_db()

        self.assertEqual(self.stock.quantity, Decimal("8.000"))
        self.assertEqual(change.delta, Decimal("-2.000"))
        self.assertEqual(change.reason, StockChange.Reason.COUNT)

    def test_recursive_stack_resolves_to_root_zone(self):
        move_unit(unit=self.unit_a, zone=self.zone1, order_key=10)
        move_unit(unit=self.unit_b, support_unit=self.unit_a, order_key=10)
        move_unit(unit=self.unit_c, support_unit=self.unit_b, order_key=10)

        self.assertEqual(resolve_effective_zone(self.unit_c), self.zone1)
        self.assertEqual(PlacementChange.objects.count(), 3)

    def test_moving_stack_root_changes_effective_zone_of_descendants(self):
        move_unit(unit=self.unit_a, zone=self.zone1, order_key=10)
        move_unit(unit=self.unit_b, support_unit=self.unit_a, order_key=10)
        move_unit(unit=self.unit_c, support_unit=self.unit_b, order_key=10)

        move_unit(unit=self.unit_a, zone=self.zone2, order_key=20)

        self.assertEqual(resolve_effective_zone(self.unit_b), self.zone2)
        self.assertEqual(resolve_effective_zone(self.unit_c), self.zone2)

    def test_cycle_is_rejected_and_existing_placement_survives(self):
        move_unit(unit=self.unit_a, zone=self.zone1)
        move_unit(unit=self.unit_b, support_unit=self.unit_a)
        move_unit(unit=self.unit_c, support_unit=self.unit_b)
        initial_changes = PlacementChange.objects.count()

        with self.assertRaises(ValidationError):
            move_unit(unit=self.unit_a, support_unit=self.unit_c)

        self.unit_a.refresh_from_db()
        self.assertEqual(self.unit_a.placement.zone, self.zone1)
        self.assertEqual(PlacementChange.objects.count(), initial_changes)

    def test_noop_move_does_not_add_audit_noise(self):
        move_unit(unit=self.unit_a, zone=self.zone1, order_key=10)
        _, change = move_unit(unit=self.unit_a, zone=self.zone1, order_key=10)

        self.assertIsNone(change)
        self.assertEqual(PlacementChange.objects.count(), 1)
