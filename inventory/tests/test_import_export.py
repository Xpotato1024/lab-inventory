import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
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
from inventory.services import adjust_stock, move_unit


class StructuredImportExportTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles", verbosity=0)
        user_model = get_user_model()
        self.viewer = user_model.objects.create_user("viewer-import", password="password-123")
        self.viewer.groups.add(Group.objects.get(name="Viewer"))
        self.editor = user_model.objects.create_user("editor-import", password="password-123")
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
        self.unit_a = PhysicalUnit.objects.create(
            code="C-001", name="Box A", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.unit_b = PhysicalUnit.objects.create(
            code="C-002", name="Box B", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.stock = Stock.objects.create(item=self.item, holder=self.unit_a, quantity=10)
        move_unit(unit=self.unit_a, zone=self.zone1, order_key=10)
        move_unit(unit=self.unit_b, support_unit=self.unit_a, order_key=10)
        PlacementChange.objects.all().delete()

    def upload(self, import_type: str, name: str, content: str):
        return self.client.post(
            reverse("inventory:structured-import"),
            {
                "import_type": import_type,
                "file": SimpleUploadedFile(
                    name,
                    content.encode("utf-8"),
                    content_type="text/csv" if name.endswith(".csv") else "application/json",
                ),
            },
        )

    def test_viewer_can_export_snapshot_but_cannot_import(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("inventory:export-snapshot"))
        self.assertEqual(response.status_code, 200)
        document = json.loads(response.content)
        self.assertEqual(document["schema"], "lab-inventory.snapshot.v1")
        self.assertEqual(document["stocks"][0]["item_code"], "I-001")

        response = self.client.get(reverse("inventory:structured-import"))
        self.assertEqual(response.status_code, 403)

    def test_stock_csv_preview_does_not_mutate_then_confirm_applies_audited_change(self):
        self.client.force_login(self.editor)
        csv_text = (
            "item_code,holder_code,operation,quantity,reason,note\n"
            "I-001,C-001,add,5,purchase,arrival\n"
        )
        response = self.upload("stock_adjust_csv", "stock.csv", csv_text)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10.000")
        self.assertContains(response, "15.000")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("10.000"))
        self.assertEqual(StockChange.objects.count(), 0)

        pending = self.client.session["lab_inventory_pending_import"]
        response = self.client.post(
            reverse("inventory:structured-import-confirm"),
            {"batch_id": pending["id"]},
        )
        self.assertRedirects(response, reverse("inventory:home"))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("15.000"))
        change = StockChange.objects.get()
        self.assertEqual(change.actor, self.editor)
        self.assertEqual(change.delta, Decimal("5.000"))

    def test_stale_preview_is_rejected_if_stock_changes_before_confirmation(self):
        self.client.force_login(self.editor)
        response = self.upload(
            "stock_adjust_csv",
            "stock.csv",
            "item_code,holder_code,operation,quantity,reason,note\n"
            "I-001,C-001,add,5,purchase,arrival\n",
        )
        self.assertEqual(response.status_code, 200)
        pending = self.client.session["lab_inventory_pending_import"]

        adjust_stock(
            stock=self.stock,
            delta=1,
            reason=StockChange.Reason.PURCHASE,
            note="another editor",
        )
        baseline_changes = StockChange.objects.count()

        response = self.client.post(
            reverse("inventory:structured-import-confirm"),
            {"batch_id": pending["id"]},
        )
        self.assertRedirects(response, reverse("inventory:structured-import"))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("11.000"))
        self.assertEqual(StockChange.objects.count(), baseline_changes)
        self.assertNotIn("lab_inventory_pending_import", self.client.session)

    def test_underflow_is_rejected_during_preview_without_mutation(self):
        self.client.force_login(self.editor)
        response = self.upload(
            "stock_adjust_csv",
            "stock.csv",
            "item_code,holder_code,operation,quantity,reason,note\n"
            "I-001,C-001,remove,11,use,too much\n",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "would become negative")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("10.000"))
        self.assertNotIn("lab_inventory_pending_import", self.client.session)

    def test_json_placement_cycle_is_rejected_during_preview(self):
        self.client.force_login(self.editor)
        document = {
            "schema": "lab-inventory.operations.v1",
            "operations": [
                {
                    "type": "move_unit",
                    "unit_code": "C-001",
                    "support_unit_code": "C-002",
                    "order_key": 10,
                }
            ],
        }
        response = self.upload("operations_json", "operations.json", json.dumps(document))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "support cycle")
        self.unit_a.refresh_from_db()
        self.assertEqual(self.unit_a.placement.zone, self.zone1)
        self.assertEqual(PlacementChange.objects.count(), 0)

    def test_placement_csv_preview_and_confirm_move_unit(self):
        self.client.force_login(self.editor)
        response = self.upload(
            "placement_csv",
            "placements.csv",
            "unit_code,zone_code,support_unit_code,order_key,note\n"
            "C-001,Z-002,,20,cleanup\n",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Z-001")
        self.assertContains(response, "Z-002")
        pending = self.client.session["lab_inventory_pending_import"]

        response = self.client.post(
            reverse("inventory:structured-import-confirm"),
            {"batch_id": pending["id"]},
        )
        self.assertRedirects(response, reverse("inventory:home"))
        self.unit_a.refresh_from_db()
        self.assertEqual(self.unit_a.placement.zone, self.zone2)
        self.assertEqual(PlacementChange.objects.count(), 1)
        self.assertEqual(PlacementChange.objects.get().actor, self.editor)
