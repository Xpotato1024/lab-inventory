from __future__ import annotations

from django import forms

from .models import Fixture, PlacementZone, Room


class StableCodeModelForm(forms.ModelForm):
    """Keep printed/public codes immutable through normal edit workflows."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and "code" in self.fields:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "作成後のIDは通常変更しません。物理ラベルとの対応を維持します。"

    def clean(self):
        cleaned = super().clean()
        for field_name in ("width_mm", "depth_mm", "height_mm"):
            value = cleaned.get(field_name)
            if value is not None and value <= 0:
                self.add_error(field_name, "寸法は0より大きい値にしてください。")
        return cleaned


class RoomForm(StableCodeModelForm):
    class Meta:
        model = Room
        fields = [
            "code",
            "name",
            "width_mm",
            "depth_mm",
            "height_mm",
            "description",
            "is_active",
        ]
        labels = {
            "code": "Room ID",
            "name": "名称",
            "width_mm": "幅 (mm)",
            "depth_mm": "奥行 (mm)",
            "height_mm": "高さ (mm)",
            "description": "メモ",
            "is_active": "使用中",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class FixtureForm(StableCodeModelForm):
    class Meta:
        model = Fixture
        fields = [
            "code",
            "name",
            "room",
            "kind",
            "width_mm",
            "depth_mm",
            "height_mm",
            "x_mm",
            "y_mm",
            "z_mm",
            "rotation_z_deg",
            "description",
            "is_active",
        ]
        labels = {
            "code": "Fixture ID",
            "name": "名称",
            "room": "部屋",
            "kind": "種別",
            "width_mm": "幅 (mm)",
            "depth_mm": "奥行 (mm)",
            "height_mm": "高さ (mm)",
            "x_mm": "X位置 (mm)",
            "y_mm": "Y位置 (mm)",
            "z_mm": "Z位置 (mm)",
            "rotation_z_deg": "水平回転 (deg)",
            "description": "メモ",
            "is_active": "使用中",
        }
        help_texts = {
            "x_mm": "部屋原点から右方向。未入力なら3Dでは仮配置します。",
            "y_mm": "部屋原点から奥方向。未入力なら3Dでは仮配置します。",
            "z_mm": "通常は床上なので0。",
            "rotation_z_deg": "上から見た水平回転。",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(is_active=True).order_by("code")


class PlacementZoneForm(StableCodeModelForm):
    class Meta:
        model = PlacementZone
        fields = [
            "code",
            "name",
            "fixture",
            "kind",
            "level_order",
            "width_mm",
            "depth_mm",
            "height_mm",
            "x_mm",
            "y_mm",
            "z_mm",
            "description",
            "is_active",
        ]
        labels = {
            "code": "Zone ID",
            "name": "名称",
            "fixture": "設備",
            "kind": "種別",
            "level_order": "段順",
            "width_mm": "幅 (mm)",
            "depth_mm": "奥行 (mm)",
            "height_mm": "高さ (mm)",
            "x_mm": "設備内X位置 (mm)",
            "y_mm": "設備内Y位置 (mm)",
            "z_mm": "設備内Z位置 (mm)",
            "description": "メモ",
            "is_active": "使用中",
        }
        help_texts = {
            "level_order": "ラック棚では下から1, 2, 3…とします。固定スロット数ではありません。",
            "x_mm": "未入力なら3D表示側で仮配置します。",
            "y_mm": "未入力なら3D表示側で仮配置します。",
            "z_mm": "棚では実測高さを入力できます。未入力なら段順から3D用高さを推定します。",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fixture"].queryset = (
            Fixture.objects.filter(is_active=True, room__is_active=True)
            .select_related("room")
            .order_by("room__code", "code")
        )
