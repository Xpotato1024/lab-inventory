from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import Fixture, PlacementZone, Room


class LayoutWorkflowTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles", verbosity=0)
        user_model = get_user_model()
        self.viewer = user_model.objects.create_user("viewer-layout", password="password")
        self.viewer.groups.add(Group.objects.get(name="Viewer"))
        self.maintainer = user_model.objects.create_user("maintainer-layout", password="password")
        self.maintainer.groups.add(Group.objects.get(name="Maintainer"))

        self.room = Room.objects.create(
            code="ROOM-A",
            name="Main lab",
            width_mm=4000,
            depth_mm=3000,
            height_mm=2400,
        )
        self.rack = Fixture.objects.create(
            code="R-001",
            name="Rack 1",
            room=self.room,
            kind=Fixture.Kind.RACK,
        )
        self.zone = PlacementZone.objects.create(
            code="Z-001",
            name="Shelf 1",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=1,
        )

    def test_viewer_cannot_open_layout_management(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("inventory:layout"))
        self.assertEqual(response.status_code, 403)

    def test_maintainer_can_open_layout_management(self):
        self.client.force_login(self.maintainer)
        response = self.client.get(reverse("inventory:layout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.room.code)
        self.assertContains(response, self.rack.code)
        self.assertContains(response, self.zone.code)

    def test_maintainer_can_create_room_without_admin(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:room-create"),
            {
                "code": "ROOM-B",
                "name": "Second lab",
                "width_mm": "5000",
                "depth_mm": "3500",
                "height_mm": "2500",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:layout"))
        self.assertTrue(Room.objects.filter(code="ROOM-B", name="Second lab").exists())

    def test_existing_room_code_is_immutable_in_normal_edit_form(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:room-edit", args=[self.room.code]),
            {
                "code": "ROOM-CHANGED",
                "name": "Renamed lab",
                "width_mm": "4000",
                "depth_mm": "3000",
                "height_mm": "2400",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:layout"))
        self.room.refresh_from_db()
        self.assertEqual(self.room.code, "ROOM-A")
        self.assertEqual(self.room.name, "Renamed lab")

    def test_new_rack_zone_defaults_to_next_level(self):
        self.client.force_login(self.maintainer)
        response = self.client.get(
            reverse("inventory:zone-create"),
            {"fixture": self.rack.code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["level_order"], 2)
        self.assertEqual(response.context["form"].initial["kind"], PlacementZone.Kind.VOLUME)

    def test_maintainer_is_not_granted_routine_delete_permissions(self):
        self.maintainer.refresh_from_db()
        self.assertFalse(self.maintainer.has_perm("inventory.delete_room"))
        self.assertFalse(self.maintainer.has_perm("inventory.delete_fixture"))
        self.assertFalse(self.maintainer.has_perm("inventory.delete_placementzone"))
        self.assertFalse(self.maintainer.has_perm("inventory.delete_physicalunit"))
