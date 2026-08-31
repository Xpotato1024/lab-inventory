from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Fixture, PhysicalUnit, PlacementZone, Room


class LabelWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("viewer", password="password")
        self.room = Room.objects.create(code="ROOM-A", name="Main lab")
        self.rack = Fixture.objects.create(
            code="R-001",
            name="Rack 1",
            room=self.room,
            kind=Fixture.Kind.RACK,
        )
        self.zone = PlacementZone.objects.create(
            code="Z-001",
            name="Shelf identity",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=2,
        )
        self.unit = PhysicalUnit.objects.create(
            code="C-001",
            name="Reusable parts box",
            kind=PhysicalUnit.Kind.CONTAINER,
        )
        self.client.force_login(self.user)

    def test_unit_qr_encodes_stable_detail_url(self):
        with patch("inventory.label_views._qr_svg", return_value="<svg></svg>") as generate:
            response = self.client.get(reverse("inventory:unit-qr", args=[self.unit.code]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("image/svg+xml"))
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        encoded_url = generate.call_args.args[0]
        self.assertTrue(encoded_url.endswith(reverse("inventory:unit-detail", args=[self.unit.code])))

    def test_zone_qr_uses_zone_detail_url(self):
        with patch("inventory.label_views._qr_svg", return_value="<svg></svg>") as generate:
            response = self.client.get(reverse("inventory:zone-qr", args=[self.zone.code]))
        self.assertEqual(response.status_code, 200)
        encoded_url = generate.call_args.args[0]
        self.assertTrue(encoded_url.endswith(reverse("inventory:zone-detail", args=[self.zone.code])))

    def test_real_qr_response_is_svg(self):
        response = self.client.get(reverse("inventory:unit-qr", args=[self.unit.code]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<svg", response.content)

    def test_label_selection_lists_zone_and_unit_identity(self):
        response = self.client.get(reverse("inventory:labels"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.zone.code)
        self.assertContains(response, self.unit.code)

    def test_print_sheet_contains_only_selected_labels(self):
        other = PhysicalUnit.objects.create(
            code="C-002",
            name="Other box",
            kind=PhysicalUnit.Kind.CONTAINER,
        )
        response = self.client.post(
            reverse("inventory:labels-print"),
            {"size": "medium", "zone": [self.zone.code], "unit": [self.unit.code]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.zone.code)
        self.assertContains(response, self.unit.code)
        self.assertNotContains(response, other.code)
        self.assertContains(response, reverse("inventory:unit-qr", args=[self.unit.code]))
        self.assertContains(response, reverse("inventory:zone-qr", args=[self.zone.code]))

    def test_qr_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:unit-qr", args=[self.unit.code]))
        self.assertEqual(response.status_code, 302)
