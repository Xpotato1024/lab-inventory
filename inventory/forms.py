from __future__ import annotations

from django import forms
from django.db import models

from .models import CatalogItem, PhysicalUnit, Placement, PlacementZone, StockChange


class StockAdjustmentForm(forms.Form):
    class Operation(models.TextChoices):
        ADD = "ADD", "追加"
        REMOVE = "REMOVE", "使用・減少"

    operation = forms.ChoiceField(label="操作", choices=Operation.choices)
    quantity = forms.DecimalField(
        label="数量",
        min_value=0.001,
        max_digits=14,
        decimal_places=3,
    )
    reason = forms.ChoiceField(
        label="理由",
        choices=[
            (StockChange.Reason.PURCHASE, "購入・入庫"),
            (StockChange.Reason.USE, "使用・出庫"),
            (StockChange.Reason.TRANSFER, "移し替え"),
            (StockChange.Reason.OTHER, "その他"),
        ],
    )
    note = forms.CharField(label="メモ", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def signed_delta(self):
        quantity = self.cleaned_data["quantity"]
        return quantity if self.cleaned_data["operation"] == self.Operation.ADD else -quantity


class StockCountForm(forms.Form):
    counted_quantity = forms.DecimalField(
        label="実際に数えた数量",
        min_value=0,
        max_digits=14,
        decimal_places=3,
    )
    note = forms.CharField(label="メモ", required=False, widget=forms.Textarea(attrs={"rows": 3}))


class StockCreateForm(forms.Form):
    item = forms.ModelChoiceField(label="品目", queryset=CatalogItem.objects.none())
    initial_quantity = forms.DecimalField(
        label="現在数量",
        min_value=0,
        max_digits=14,
        decimal_places=3,
        initial=0,
    )
    note = forms.CharField(label="メモ", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, holder: PhysicalUnit, **kwargs):
        super().__init__(*args, **kwargs)
        existing_item_ids = holder.stocks.values_list("item_id", flat=True)
        self.fields["item"].queryset = CatalogItem.objects.filter(
            tracking_mode=CatalogItem.TrackingMode.QUANTITY,
            is_active=True,
        ).exclude(pk__in=existing_item_ids)


class MoveUnitForm(forms.Form):
    class TargetType(models.TextChoices):
        ZONE = "ZONE", "棚・机・壁面などへ置く"
        SUPPORT = "SUPPORT", "別の物の上へ置く"

    class Position(models.TextChoices):
        LEFTMOST = "LEFTMOST", "左端"
        RIGHTMOST = "RIGHTMOST", "右端"
        BEFORE = "BEFORE", "指定した物の左"
        AFTER = "AFTER", "指定した物の右"

    target_type = forms.ChoiceField(
        label="配置方法",
        choices=TargetType.choices,
        widget=forms.RadioSelect,
    )
    zone = forms.ModelChoiceField(
        label="配置先",
        queryset=PlacementZone.objects.none(),
        required=False,
    )
    support_unit = forms.ModelChoiceField(
        label="下になる物",
        queryset=PhysicalUnit.objects.none(),
        required=False,
    )
    position = forms.ChoiceField(
        label="左右位置",
        choices=Position.choices,
        initial=Position.RIGHTMOST,
    )
    reference_unit = forms.ModelChoiceField(
        label="基準にする物",
        queryset=PhysicalUnit.objects.none(),
        required=False,
        help_text="「指定した物の左/右」を選ぶ場合だけ指定します。",
    )
    note = forms.CharField(label="メモ", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, unit: PhysicalUnit, **kwargs):
        super().__init__(*args, **kwargs)
        self.unit = unit
        self.fields["zone"].queryset = PlacementZone.objects.filter(
            is_active=True,
            fixture__is_active=True,
            fixture__room__is_active=True,
        ).select_related("fixture", "fixture__room")
        available_units = PhysicalUnit.objects.filter(is_active=True).exclude(pk=unit.pk)
        self.fields["support_unit"].queryset = available_units
        self.fields["reference_unit"].queryset = available_units

    def clean(self):
        cleaned = super().clean()
        target_type = cleaned.get("target_type")
        zone = cleaned.get("zone")
        support_unit = cleaned.get("support_unit")
        position = cleaned.get("position")
        reference_unit = cleaned.get("reference_unit")

        if target_type == self.TargetType.ZONE:
            if zone is None:
                self.add_error("zone", "配置先を選択してください。")
            cleaned["support_unit"] = None
            support_unit = None
        elif target_type == self.TargetType.SUPPORT:
            if support_unit is None:
                self.add_error("support_unit", "下になる物を選択してください。")
            cleaned["zone"] = None
            zone = None

        if position in {self.Position.BEFORE, self.Position.AFTER}:
            if reference_unit is None:
                self.add_error("reference_unit", "左右の基準にする物を選択してください。")
            elif zone is not None and not Placement.objects.filter(
                unit=reference_unit, zone=zone
            ).exists():
                self.add_error("reference_unit", "基準にする物は選択した配置先にありません。")
            elif support_unit is not None and not Placement.objects.filter(
                unit=reference_unit, support_unit=support_unit
            ).exists():
                self.add_error("reference_unit", "基準にする物は同じ物の上にありません。")
        else:
            cleaned["reference_unit"] = None

        return cleaned


class StructuredImportForm(forms.Form):
    class ImportType(models.TextChoices):
        STOCK_ADJUST_CSV = "stock_adjust_csv", "在庫増減 CSV"
        STOCK_COUNT_CSV = "stock_count_csv", "棚卸 CSV"
        PLACEMENT_CSV = "placement_csv", "配置変更 CSV"
        OPERATIONS_JSON = "operations_json", "Operation JSON"

    import_type = forms.ChoiceField(label="形式", choices=ImportType.choices)
    file = forms.FileField(
        label="ファイル",
        help_text="UTF-8、最大1 MB。内容は検証・previewされ、確認するまで反映されません。",
    )
