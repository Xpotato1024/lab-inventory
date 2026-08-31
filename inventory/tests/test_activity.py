from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import CatalogItem, Fixture, PhysicalUnit, PlacementZone, Room, StockChange
from inventory.services import adjust_stock, create_stock, move_unit


class ActivityViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("activity-user", password="password")
        self.room = Room.objects.create(code="ROOM-A", name="Main lab")
        self.rack = Fixture.objects.create(
            code="R-001", name="Rack 1", room=self.room, kind=Fixture.Kind.RACK
        )
        self.zone1 = PlacementZone.objects.create(
            code="Z-001", name="Shelf 1", fixture=self.rack, kind=PlacementZone.Kind.VOLUME
        )
        self.zone2 = PlacementZone.objects.create(
            code="Z-002", name="Shelf 2", fixture=self.rack, kind=PlacementZone.Kind.VOLUME
        )
        self.unit = PhysicalUnit.objects.create(
            code="C-001", name="Parts box", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.item = CatalogItem.objects.create(
            code="I-001",
            name="M3 bolt",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
        )
        self.stock, _ = create_stock(
            item=self.item,
            holder=self.unit,
            initial_quantity=10,
            actor=self.user,
            note="initial count",
        )
        adjust_stock(
            stock=self.stock,
            delta=-2,
            reason=StockChange.Reason.USE,
            actor=self.user,
            note="prototype",
        )
        move_unit(unit=self.unit, zone=self.zone1, actor=self.user, note="initial placement")
        move_unit(unit=self.unit, zone=self.zone2, actor=self.user, note="cleanup move")
        self.client.force_login(self.user)

    def test_activity_page_shows_stock_and_placement_audit(self):
        response = self.client.get(reverse("inventory:activity"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "I-001")
        self.assertContains(response, "C-001")
        self.assertContains(response, "prototype")
        self.assertContains(response, "cleanup move")
        self.assertContains(response, self.user.username)

    def test_activity_filter_matches_note_and_entity_codes(self):
        response = self.client.get(reverse("inventory:activity"), {"q": "prototype"})
        self.assertContains(response, "prototype")
        self.assertNotContains(response, "cleanup move")

        response = self.client.get(reverse("inventory:activity"), {"q": "Z-002"})
        self.assertContains(response, "cleanup move")

    def test_activity_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:activity"))
        self.assertEqual(response.status_code, 302)
