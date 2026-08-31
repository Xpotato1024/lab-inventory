from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Fixture, PhysicalUnit, PlacementZone, Room
from inventory.scene import build_room_scene
from inventory.services import move_unit


class ProceduralSceneTests(TestCase):
    def setUp(self):
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
            width_mm=1200,
            depth_mm=500,
            height_mm=1800,
            x_mm=200,
            y_mm=300,
            z_mm=0,
        )
        self.shelf1 = PlacementZone.objects.create(
            code="Z-001",
            name="Shelf 1",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=1,
        )
        self.shelf2 = PlacementZone.objects.create(
            code="Z-002",
            name="Shelf 2",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=2,
        )
        self.box = PhysicalUnit.objects.create(
            code="C-001",
            name="Large box",
            kind=PhysicalUnit.Kind.CONTAINER,
            width_mm=400,
            depth_mm=250,
            height_mm=180,
        )
        self.child = PhysicalUnit.objects.create(
            code="C-002",
            name="Small box",
            kind=PhysicalUnit.Kind.CONTAINER,
            width_mm=180,
            depth_mm=120,
            height_mm=90,
        )
        move_unit(unit=self.box, zone=self.shelf1, order_key=10)
        move_unit(unit=self.child, support_unit=self.box, order_key=10)

    def test_shelf_level_order_produces_ascending_display_height(self):
        scene = build_room_scene(self.room)
        zones = {zone["code"]: zone for zone in scene["zones"]}
        self.assertLess(zones["Z-001"]["origin_mm"][2], zones["Z-002"]["origin_mm"][2])

    def test_stacked_child_is_positioned_on_parent_top(self):
        scene = build_room_scene(self.room)
        units = {unit["code"]: unit for unit in scene["units"]}
        parent = units["C-001"]
        child = units["C-002"]
        parent_top = parent["origin_mm"][2] + parent["size_mm"][2]
        self.assertGreaterEqual(child["origin_mm"][2], parent_top)
        self.assertEqual(child["support_unit_code"], "C-001")
        self.assertEqual(child["root_zone_code"], "Z-001")

    def test_missing_unit_dimensions_use_placeholder_without_blocking_scene(self):
        unknown = PhysicalUnit.objects.create(
            code="U-003",
            name="Unknown carton",
            kind=PhysicalUnit.Kind.CARTON,
        )
        move_unit(unit=unknown, zone=self.shelf2, order_key=20)
        scene = build_room_scene(self.room)
        unit = next(node for node in scene["units"] if node["code"] == "U-003")
        self.assertTrue(unit["auto_geometry"])
        self.assertTrue(any("placeholder dimensions" in warning for warning in scene["warnings"]))


class ProceduralSceneViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("viewer", password="password")
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
            width_mm=1200,
            depth_mm=500,
            height_mm=1800,
            x_mm=200,
            y_mm=300,
        )
        self.zone = PlacementZone.objects.create(
            code="Z-001",
            name="Shelf 1",
            fixture=self.rack,
            kind=PlacementZone.Kind.VOLUME,
            level_order=1,
        )
        self.unit = PhysicalUnit.objects.create(
            code="C-001",
            name="Parts box",
            kind=PhysicalUnit.Kind.CONTAINER,
            width_mm=300,
            depth_mm=200,
            height_mm=120,
        )
        move_unit(unit=self.unit, zone=self.zone)
        self.client.force_login(self.user)

    def test_unit_focus_selects_effective_room_and_highlight(self):
        response = self.client.get(reverse("inventory:room-3d"), {"unit": self.unit.code})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(
            response.context["scene_data"]["highlight"],
            {"type": "unit", "code": self.unit.code},
        )
        self.assertEqual(
            response.context["scene_data"]["links"]["units"][self.unit.code],
            reverse("inventory:unit-detail", args=[self.unit.code]),
        )
        self.assertContains(response, "three@0.185.1")

    def test_zone_focus_selects_room_and_highlight(self):
        response = self.client.get(reverse("inventory:room-3d"), {"zone": self.zone.code})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(
            response.context["scene_data"]["highlight"],
            {"type": "zone", "code": self.zone.code},
        )

    def test_3d_view_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:room-3d"))
        self.assertEqual(response.status_code, 302)
