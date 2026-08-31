from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import CatalogItem, PhysicalUnit, Stock
from inventory.status import low_stock_items


class LowStockStatusTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("status-viewer", password="password")
        self.box1 = PhysicalUnit.objects.create(
            code="C-101", name="Box 1", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.box2 = PhysicalUnit.objects.create(
            code="C-102", name="Box 2", kind=PhysicalUnit.Kind.CONTAINER
        )
        self.low = CatalogItem.objects.create(
            code="I-101",
            name="Low bolts",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
            minimum_stock=100,
        )
        self.ok = CatalogItem.objects.create(
            code="I-102",
            name="Enough nuts",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
            minimum_stock=100,
        )
        self.zero = CatalogItem.objects.create(
            code="I-103",
            name="Missing washers",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
            minimum_stock=25,
        )
        self.no_threshold = CatalogItem.objects.create(
            code="I-104",
            name="Unmanaged threshold",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
        )
        self.inactive = CatalogItem.objects.create(
            code="I-105",
            name="Retired item",
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            unit="pcs",
            minimum_stock=999,
            is_active=False,
        )

        Stock.objects.create(item=self.low, holder=self.box1, quantity=30)
        Stock.objects.create(item=self.low, holder=self.box2, quantity=20)
        Stock.objects.create(item=self.ok, holder=self.box1, quantity=120)
        Stock.objects.create(item=self.no_threshold, holder=self.box2, quantity=0)

    def test_low_stock_aggregates_across_multiple_holders(self):
        items = {item.code: item for item in low_stock_items()}
        self.assertEqual(items["I-101"].total_stock, Decimal("50"))
        self.assertEqual(items["I-101"].shortage, Decimal("50"))
        self.assertNotIn("I-102", items)

    def test_zero_stock_item_is_included(self):
        items = {item.code: item for item in low_stock_items()}
        self.assertEqual(items["I-103"].total_stock, Decimal("0"))
        self.assertEqual(items["I-103"].shortage, Decimal("25"))

    def test_items_without_threshold_and_inactive_items_are_excluded(self):
        codes = set(low_stock_items().values_list("code", flat=True))
        self.assertNotIn("I-104", codes)
        self.assertNotIn("I-105", codes)

    def test_low_stock_page_lists_shortage_and_holder_links(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("inventory:low-stock"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "I-101")
        self.assertContains(response, "I-103")
        self.assertContains(response, "C-101")
        self.assertNotContains(response, "I-102")

    def test_home_surfaces_low_stock_count(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("inventory:home"))
        self.assertContains(response, "在庫不足 2件")

    def test_low_stock_page_requires_login(self):
        response = self.client.get(reverse("inventory:low-stock"))
        self.assertEqual(response.status_code, 302)
