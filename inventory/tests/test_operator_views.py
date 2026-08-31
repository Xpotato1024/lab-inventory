from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

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
from inventory.services import move_unit


class OperatorWorkflowTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles", verbosity=0)
        user_model = get_user_model()
        self.viewer = user_model.objects.create_user("viewer", password="viewer-password")
        self.viewer.groups.add(Group.objects.get(name="Viewer"))
        self.editor = user_model.objects.create_user("editor", password="editor-password")
        self.editor.groups.add(Group.objects.get(name="Editor"))

        self.room = Room.objects.create(code="ROOM-A", name="Main lab")
        self.rack = Fixture.objects.create(
            code="R-001", name="Rack 1", room=self.room, kind=Fixture.Kind.RACK
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
        self.holder = PhysicalUnit.objects.create(
            code="C-001", name="Parts box", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.second_holder = PhysicalUnit.objects.create(
            code="C-002", name="Empty box", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.stock = Stock.objects.create(item=self.item, holder=self.holder, quantity=10)
        move_unit(unit=self.holder, zone=self.zone1, order_key=10)

    def test_authenticated_search_finds_items_units_and_zones(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("inventory:home"), {"q": "M3"})
        self.assertContains(response, "I-001")
        response = self.client.get(reverse("inventory:home"), {"q": "C-001"})
        self.assertContains(response, "Parts box")
        response = self.client.get(reverse("inventory:home"), {"q": "Z-001"})
        self.assertContains(response, "Shelf 1")

    def test_viewer_cannot_mutate_stock(self):
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("inventory:stock-adjust", args=[self.stock.pk]),
            {"operation": "ADD", "quantity": "5", "reason": "PURCHASE", "note": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("10.000"))

    def test_editor_can_adjust_stock_through_audited_view(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("inventory:stock-adjust", args=[self.stock.pk]),
            {"operation": "ADD", "quantity": "5", "reason": "PURCHASE", "note": "arrival"},
        )
        self.assertRedirects(response, reverse("inventory:unit-detail", args=[self.holder.code]))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("15.000"))
        change = StockChange.objects.latest("created_at")
        self.assertEqual(change.actor, self.editor)
        self.assertEqual(change.delta, Decimal("5.000"))

    def test_editor_can_reconcile_count(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("inventory:stock-count", args=[self.stock.pk]),
            {"counted_quantity": "8", "note": "physical count"},
        )
        self.assertRedirects(response, reverse("inventory:unit-detail", args=[self.holder.code]))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("8.000"))
        self.assertEqual(StockChange.objects.latest("created_at").reason, StockChange.Reason.COUNT)

    def test_editor_can_register_new_stock_holder_item(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("inventory:stock-create", args=[self.second_holder.code]),
            {"item": str(self.item.pk), "initial_quantity": "12", "note": "initial count"},
        )
        self.assertRedirects(
            response,
            reverse("inventory:unit-detail", args=[self.second_holder.code]),
        )
        stock = Stock.objects.get(item=self.item, holder=self.second_holder)
        self.assertEqual(stock.quantity, Decimal("12.000"))
        self.assertEqual(stock.changes.count(), 1)
        self.assertEqual(stock.changes.get().actor, self.editor)

    def test_editor_can_move_unit_and_change_is_audited(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("inventory:unit-move", args=[self.holder.code]),
            {
                "target_type": "ZONE",
                "zone": str(self.zone2.pk),
                "support_unit": "",
                "order_key": "20",
                "note": "cleanup",
            },
        )
        self.assertRedirects(response, reverse("inventory:unit-detail", args=[self.holder.code]))
        self.holder.refresh_from_db()
        self.assertEqual(self.holder.placement.zone, self.zone2)
        latest = PlacementChange.objects.latest("created_at")
        self.assertEqual(latest.actor, self.editor)
        self.assertEqual(latest.to_zone, self.zone2)
