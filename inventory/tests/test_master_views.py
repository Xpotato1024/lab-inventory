from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import CatalogItem, PhysicalUnit, Stock


class MasterDataWorkflowTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles", verbosity=0)
        user_model = get_user_model()
        self.viewer = user_model.objects.create_user("viewer-master", password="password")
        self.viewer.groups.add(Group.objects.get(name="Viewer"))
        self.maintainer = user_model.objects.create_user("maintainer-master", password="password")
        self.maintainer.groups.add(Group.objects.get(name="Maintainer"))

        self.item = CatalogItem.objects.create(
            code="I-001",
            name="M3 bolt",
            category="fastener",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
        )
        self.holder = PhysicalUnit.objects.create(
            code="C-001",
            name="Parts box",
            kind=PhysicalUnit.Kind.CONTAINER,
        )

    def test_viewer_cannot_open_master_management(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("inventory:master"))
        self.assertEqual(response.status_code, 403)

    def test_maintainer_can_open_master_management(self):
        self.client.force_login(self.maintainer)
        response = self.client.get(reverse("inventory:master"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.item.code)
        self.assertContains(response, self.holder.code)

    def test_maintainer_can_create_quantity_item(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:item-create"),
            {
                "code": "I-002",
                "name": "PLA black",
                "category": "filament",
                "tracking_mode": CatalogItem.TrackingMode.QUANTITY,
                "unit": "g",
                "minimum_stock": "500",
                "manufacturer": "",
                "part_number": "",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:master"))
        item = CatalogItem.objects.get(code="I-002")
        self.assertEqual(item.unit, "g")
        self.assertEqual(str(item.minimum_stock), "500.000")

    def test_quantity_item_requires_unit(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:item-create"),
            {
                "code": "I-003",
                "name": "No unit item",
                "category": "",
                "tracking_mode": CatalogItem.TrackingMode.QUANTITY,
                "unit": "",
                "minimum_stock": "",
                "manufacturer": "",
                "part_number": "",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "数量管理品には単位を入力してください")
        self.assertFalse(CatalogItem.objects.filter(code="I-003").exists())

    def test_existing_item_code_is_immutable(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:item-edit", args=[self.item.code]),
            {
                "code": "I-CHANGED",
                "name": "Renamed bolt",
                "category": "fastener",
                "tracking_mode": CatalogItem.TrackingMode.QUANTITY,
                "unit": "pcs",
                "minimum_stock": "",
                "manufacturer": "",
                "part_number": "",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:master"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.code, "I-001")
        self.assertEqual(self.item.name, "Renamed bolt")

    def test_tracking_mode_is_locked_after_stock_exists(self):
        Stock.objects.create(item=self.item, holder=self.holder, quantity=10)
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:item-edit", args=[self.item.code]),
            {
                "code": self.item.code,
                "name": self.item.name,
                "category": self.item.category,
                "tracking_mode": CatalogItem.TrackingMode.INDIVIDUAL,
                "unit": "pcs",
                "minimum_stock": "",
                "manufacturer": "",
                "part_number": "",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:master"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.tracking_mode, CatalogItem.TrackingMode.QUANTITY)

    def test_maintainer_can_create_physical_unit_without_dimensions(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:unit-create"),
            {
                "code": "U-002",
                "name": "Unmeasured power supply",
                "kind": PhysicalUnit.Kind.EQUIPMENT,
                "catalog_item": "",
                "width_mm": "",
                "depth_mm": "",
                "height_mm": "",
                "description": "",
                "is_active": "on",
            },
        )
        unit = PhysicalUnit.objects.get(code="U-002")
        self.assertRedirects(response, reverse("inventory:unit-detail", args=[unit.code]))
        self.assertIsNone(unit.width_mm)

    def test_existing_physical_unit_code_is_immutable(self):
        self.client.force_login(self.maintainer)
        response = self.client.post(
            reverse("inventory:unit-edit", args=[self.holder.code]),
            {
                "code": "C-CHANGED",
                "name": "Renamed box",
                "kind": PhysicalUnit.Kind.CONTAINER,
                "catalog_item": "",
                "width_mm": "",
                "depth_mm": "",
                "height_mm": "",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:unit-detail", args=[self.holder.code]))
        self.holder.refresh_from_db()
        self.assertEqual(self.holder.code, "C-001")
        self.assertEqual(self.holder.name, "Renamed box")
