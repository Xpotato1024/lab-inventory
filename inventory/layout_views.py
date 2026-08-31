from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Max, Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .layout_forms import FixtureForm, PlacementZoneForm, RoomForm
from .models import Fixture, PlacementZone, Room


@login_required
@permission_required("inventory.view_room", raise_exception=True)
def layout_index(request):
    zones = PlacementZone.objects.order_by("level_order", "code")
    fixtures = Fixture.objects.prefetch_related(Prefetch("zones", queryset=zones)).order_by("code")
    rooms = Room.objects.prefetch_related(Prefetch("fixtures", queryset=fixtures)).order_by("code")
    return render(request, "inventory/layout_index.html", {"rooms": rooms})


@login_required
@permission_required("inventory.add_room", raise_exception=True)
def room_create(request):
    form = RoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        room = form.save()
        messages.success(request, f"{room.code} を作成しました。")
        return redirect("inventory:layout")
    return render(
        request,
        "inventory/layout_form.html",
        {"form": form, "title": "部屋を追加", "entity_label": "Room"},
    )


@login_required
@permission_required("inventory.change_room", raise_exception=True)
def room_edit(request, code: str):
    room = get_object_or_404(Room, code=code)
    form = RoomForm(request.POST or None, instance=room)
    if request.method == "POST" and form.is_valid():
        room = form.save()
        messages.success(request, f"{room.code} を更新しました。")
        return redirect("inventory:layout")
    return render(
        request,
        "inventory/layout_form.html",
        {"form": form, "title": f"{room.code} を編集", "entity_label": "Room"},
    )


@login_required
@permission_required("inventory.add_fixture", raise_exception=True)
def fixture_create(request):
    initial = {}
    room_code = request.GET.get("room", "").strip()
    if room_code:
        room = Room.objects.filter(code=room_code, is_active=True).first()
        if room:
            initial["room"] = room

    form = FixtureForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        fixture = form.save()
        messages.success(request, f"{fixture.code} を作成しました。")
        return redirect("inventory:layout")
    return render(
        request,
        "inventory/layout_form.html",
        {"form": form, "title": "設備を追加", "entity_label": "Fixture"},
    )


@login_required
@permission_required("inventory.change_fixture", raise_exception=True)
def fixture_edit(request, code: str):
    fixture = get_object_or_404(Fixture, code=code)
    form = FixtureForm(request.POST or None, instance=fixture)
    if request.method == "POST" and form.is_valid():
        fixture = form.save()
        messages.success(request, f"{fixture.code} を更新しました。")
        return redirect("inventory:layout")
    return render(
        request,
        "inventory/layout_form.html",
        {"form": form, "title": f"{fixture.code} を編集", "entity_label": "Fixture"},
    )


@login_required
@permission_required("inventory.add_placementzone", raise_exception=True)
def zone_create(request):
    initial = {}
    fixture_code = request.GET.get("fixture", "").strip()
    fixture = None
    if fixture_code:
        fixture = Fixture.objects.filter(
            code=fixture_code,
            is_active=True,
            room__is_active=True,
        ).first()
    if fixture:
        initial["fixture"] = fixture
        if fixture.kind == Fixture.Kind.RACK:
            highest = fixture.zones.aggregate(highest=Max("level_order"))["highest"] or 0
            initial["kind"] = PlacementZone.Kind.VOLUME
            initial["level_order"] = highest + 1
            initial["name"] = f"棚 {highest + 1}"
        elif fixture.kind in (Fixture.Kind.DESK, Fixture.Kind.WORKBENCH):
            initial["kind"] = PlacementZone.Kind.SURFACE
        elif fixture.kind == Fixture.Kind.WALL:
            initial["kind"] = PlacementZone.Kind.WALL

    form = PlacementZoneForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        zone = form.save()
        messages.success(request, f"{zone.code} を作成しました。")
        return redirect("inventory:layout")
    return render(
        request,
        "inventory/layout_form.html",
        {"form": form, "title": "Placement Zoneを追加", "entity_label": "Placement Zone"},
    )


@login_required
@permission_required("inventory.change_placementzone", raise_exception=True)
def zone_edit(request, code: str):
    zone = get_object_or_404(PlacementZone, code=code)
    form = PlacementZoneForm(request.POST or None, instance=zone)
    if request.method == "POST" and form.is_valid():
        zone = form.save()
        messages.success(request, f"{zone.code} を更新しました。")
        return redirect("inventory:layout")
    return render(
        request,
        "inventory/layout_form.html",
        {"form": form, "title": f"{zone.code} を編集", "entity_label": "Placement Zone"},
    )
