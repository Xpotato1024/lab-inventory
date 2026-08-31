from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Fixture, PhysicalUnit, PlacementZone, Room
from .scene import build_room_scene
from .services import resolve_effective_zone


@login_required
def room_3d(request):
    rooms = Room.objects.filter(is_active=True).order_by("code")
    room = None
    highlight: dict[str, str] | None = None
    page_warnings: list[str] = []

    unit_code = request.GET.get("unit", "").strip()
    zone_code = request.GET.get("zone", "").strip()
    fixture_code = request.GET.get("fixture", "").strip()
    room_code = request.GET.get("room", "").strip()

    if unit_code:
        unit = get_object_or_404(PhysicalUnit, code=unit_code, is_active=True)
        effective_zone = resolve_effective_zone(unit)
        if effective_zone is not None:
            room = effective_zone.fixture.room
        else:
            page_warnings.append(
                f"{unit.code} は通常保管位置が未登録のため、3D上の位置を特定できません。"
            )
        highlight = {"type": "unit", "code": unit.code}
    elif zone_code:
        zone = get_object_or_404(
            PlacementZone.objects.select_related("fixture__room"),
            code=zone_code,
            is_active=True,
        )
        room = zone.fixture.room
        highlight = {"type": "zone", "code": zone.code}
    elif fixture_code:
        fixture = get_object_or_404(
            Fixture.objects.select_related("room"), code=fixture_code, is_active=True
        )
        room = fixture.room
        highlight = {"type": "fixture", "code": fixture.code}

    if room is None and room_code:
        room = get_object_or_404(Room, code=room_code, is_active=True)
    if room is None:
        room = rooms.first()

    scene_data = None
    if room is not None:
        scene_data = build_room_scene(room)
        scene_data["highlight"] = highlight
        scene_data["links"] = {
            "zones": {
                node["code"]: reverse("inventory:zone-detail", args=[node["code"]])
                for node in scene_data["zones"]
            },
            "units": {
                node["code"]: reverse("inventory:unit-detail", args=[node["code"]])
                for node in scene_data["units"]
            },
        }

    return render(
        request,
        "inventory/room_3d.html",
        {
            "rooms": rooms,
            "room": room,
            "scene_data": scene_data,
            "page_warnings": page_warnings,
        },
    )
