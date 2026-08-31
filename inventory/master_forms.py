from __future__ import annotations

from django import forms
from django.db.models import Q

from .layout_forms import StableCodeModelForm
from .models import CatalogItem, PhysicalUnit


class CatalogItemForm(StableCodeModelForm):
    class Meta:
        model = CatalogItem
        fields = [
            "code",
            "name",
            "category",
            "tracking_mode",
            "unit",
            "minimum_stock",
            "manufacturer",
            "part_number",
            "description",
            "is_active",
        ]
        labels = {
            "code": "Item ID",
            "name": "品名",
            "category": "カテゴリ",
            "tracking_mode": "管理方式",
            "unit": "数量単位",
            "minimum_stock": "最低在庫目安",
            "manufacturer": "メーカー",
            "part_number": "型番",
            "description": "メモ",
            "is_active": "使用中",
        }
        help_texts = {
            "tracking_mode": "ネジ・フィラメント等は数量管理、個別に追跡する機器・工具は個体管理を選択します。",
            "unit": "数量管理なら pcs, g, m など。個体管理では通常空欄です。",
            "minimum_stock": "未入力なら在庫警告の基準を設けません。",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance._state.adding:
            # Changing tracking semantics after stock/instances exist makes historical
            # records ambiguous. Keep it stable through the normal maintainer UI.
            if self.instance.stocks.exists() or self.instance.physical_units.exists():
                self.fields["tracking_mode"].disabled = True
                self.fields["tracking_mode"].help_text = (
                    "在庫または個体が登録済みのため、管理方式は通常画面から変更できません。"
                )

    def clean(self):
        cleaned = super().clean()
        tracking_mode = cleaned.get("tracking_mode")
        unit = (cleaned.get("unit") or "").strip()
        minimum_stock = cleaned.get("minimum_stock")

        if tracking_mode == CatalogItem.TrackingMode.QUANTITY and not unit:
            self.add_error("unit", "数量管理品には単位を入力してください（例: pcs, g, m）。")
        if minimum_stock is not None and minimum_stock < 0:
            self.add_error("minimum_stock", "最低在庫目安は0以上にしてください。")
        return cleaned


class PhysicalUnitForm(StableCodeModelForm):
    class Meta:
        model = PhysicalUnit
        fields = [
            "code",
            "name",
            "kind",
            "catalog_item",
            "width_mm",
            "depth_mm",
            "height_mm",
            "description",
            "is_active",
        ]
        labels = {
            "code": "Unit ID",
            "name": "名称",
            "kind": "種別",
            "catalog_item": "対応する品目（任意）",
            "width_mm": "幅 (mm)",
            "depth_mm": "奥行 (mm)",
            "height_mm": "高さ (mm)",
            "description": "メモ",
            "is_active": "使用中",
        }
        help_texts = {
            "catalog_item": "型式としてCatalogItemと結び付けたい個体だけ選択します。収納箱は通常空欄です。",
            "width_mm": "未測定でも登録できます。3Dでは種別ごとの仮寸法を使います。",
            "depth_mm": "未測定でも登録できます。",
            "height_mm": "未測定でも登録できます。",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        query = Q(is_active=True)
        if (
            self.instance
            and not self.instance._state.adding
            and self.instance.catalog_item_id is not None
        ):
            query |= Q(pk=self.instance.catalog_item_id)
        self.fields["catalog_item"].queryset = CatalogItem.objects.filter(query).order_by("code")
