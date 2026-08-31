import json
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import StructuredImportForm
from .import_export import (
    ImportValidationError,
    apply_validated_batch,
    parse_import,
    validate_operations,
)
from .models import CatalogItem, Fixture, PhysicalUnit, Placement, PlacementZone, Room, Stock

PENDING_IMPORT_SESSION_KEY = "lab_inventory_pending_import"
PENDING_IMPORT_MAX_AGE_SECONDS = 30 * 60


@login_required
def structured_import(request: HttpRequest) -> HttpResponse:
    if not (
        request.user.has_perm("inventory.change_stock")
        or request.user.has_perm("inventory.change_placement")
    ):
        raise PermissionDenied("Structured import requires Editor or Maintainer permissions.")

    form = StructuredImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            operations = parse_import(form.cleaned_data["import_type"], form.cleaned_data["file"])
            batch = validate_operations(operations, user=request.user)
        except ImportValidationError as exc:
            form.add_error("file", exc.messages)
        else:
            batch_id = secrets.token_urlsafe(18)
            request.session[PENDING_IMPORT_SESSION_KEY] = {
                "id": batch_id,
                "created_at": timezone.now().timestamp(),
                "payload": batch.session_payload(),
                "preview": batch.preview,
                "import_type": form.cleaned_data["import_type"],
            }
            request.session.modified = True
            return render(
                request,
                "inventory/import_preview.html",
                {"batch_id": batch_id, "preview": batch.preview},
            )

    return render(request, "inventory/import_upload.html", {"form": form})


@login_required
def structured_import_confirm(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("inventory:structured-import")

    pending = request.session.get(PENDING_IMPORT_SESSION_KEY)
    batch_id = request.POST.get("batch_id", "")
    if not pending or not secrets.compare_digest(str(pending.get("id", "")), batch_id):
        messages.error(request, "Import previewが見つからないか、別のpreviewに置き換わっています。")
        return redirect("inventory:structured-import")

    created_at = float(pending.get("created_at", 0))
    if timezone.now().timestamp() - created_at > PENDING_IMPORT_MAX_AGE_SECONDS:
        request.session.pop(PENDING_IMPORT_SESSION_KEY, None)
        messages.error(request, "Import previewの有効期限が切れました。もう一度previewしてください。")
        return redirect("inventory:structured-import")

    try:
        applied = apply_validated_batch(pending["payload"], user=request.user)
    except ImportValidationError as exc:
        request.session.pop(PENDING_IMPORT_SESSION_KEY, None)
        messages.error(request, "反映できませんでした: " + " ".join(exc.messages))
        return redirect("inventory:structured-import")

    request.session.pop(PENDING_IMPORT_SESSION_KEY, None)
    messages.success(request, f"{applied}件の操作を一括反映しました。")
    return redirect("inventory:home")


@login_required
def export_snapshot(request: HttpRequest) -> HttpResponse:
    generated_at = timezone.now().isoformat()
    rooms = Room.objects.all()
    fixtures = Fixture.objects.select_related("room").all()
    zones = PlacementZone.objects.select_related("fixture").all()
    items = CatalogItem.objects.all()
    units = PhysicalUnit.objects.select_related("catalog_item").all()
    placements = Placement.objects.select_related("unit", "zone", "support_unit").all()
    stocks = Stock.objects.select_related("item", "holder").all()

    document = {
        "schema": "lab-inventory.snapshot.v1",
        "generated_at": generated_at,
        "warning": "Snapshot export only. Do not use an old snapshot to silently overwrite current state.",
        "rooms": [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "dimensions_mm": _dimensions(room),
                "active": room.is_active,
            }
            for room in rooms
        ],
        "fixtures": [
            {
                "id": str(fixture.id),
                "code": fixture.code,
                "name": fixture.name,
                "kind": fixture.kind,
                "room_code": fixture.room.code,
                "dimensions_mm": _dimensions(fixture),
                "position_mm": _position(fixture),
                "rotation_z_deg": _string_or_none(fixture.rotation_z_deg),
                "active": fixture.is_active,
            }
            for fixture in fixtures
        ],
        "placement_zones": [
            {
                "id": str(zone.id),
                "code": zone.code,
                "name": zone.name,
                "kind": zone.kind,
                "fixture_code": zone.fixture.code,
                "level_order": zone.level_order,
                "dimensions_mm": _dimensions(zone),
                "active": zone.is_active,
            }
            for zone in zones
        ],
        "catalog_items": [
            {
                "id": str(item.id),
                "code": item.code,
                "name": item.name,
                "category": item.category,
                "tracking_mode": item.tracking_mode,
                "unit": item.unit,
                "minimum_stock": _string_or_none(item.minimum_stock),
                "manufacturer": item.manufacturer,
                "part_number": item.part_number,
                "active": item.is_active,
            }
            for item in items
        ],
        "physical_units": [
            {
                "id": str(unit.id),
                "code": unit.code,
                "name": unit.name,
                "kind": unit.kind,
                "catalog_item_code": unit.catalog_item.code if unit.catalog_item else None,
                "dimensions_mm": _dimensions(unit),
                "active": unit.is_active,
            }
            for unit in units
        ],
        "placements": [
            {
                "unit_code": placement.unit.code,
                "zone_code": placement.zone.code if placement.zone else None,
                "support_unit_code": placement.support_unit.code if placement.support_unit else None,
                "order_key": placement.order_key,
            }
            for placement in placements
        ],
        "stocks": [
            {
                "item_code": stock.item.code,
                "holder_code": stock.holder.code,
                "quantity": str(stock.quantity),
                "unit": stock.item.unit,
            }
            for stock in stocks
        ],
    }

    response = HttpResponse(
        json.dumps(document, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="lab-inventory-snapshot.json"'
    return response


def _string_or_none(value):
    return str(value) if value is not None else None


def _dimensions(instance):
    return [
        _string_or_none(instance.width_mm),
        _string_or_none(instance.depth_mm),
        _string_or_none(instance.height_mm),
    ]


def _position(instance):
    return [
        _string_or_none(instance.x_mm),
        _string_or_none(instance.y_mm),
        _string_or_none(instance.z_mm),
    ]
