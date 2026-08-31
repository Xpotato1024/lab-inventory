import json
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    MoveUnitForm,
    StockAdjustmentForm,
    StockCountForm,
    StockCreateForm,
    StructuredImportForm,
)
from .import_export import (
    ImportValidationError,
    SCHEMA_VERSION,
    apply_validated_batch,
    parse_import,
    validate_operations,
)
from .models import (
    CatalogItem,
    Fixture,
    PhysicalUnit,
    Placement,
    PlacementZone,
    Room,
    Stock,
    StockChange,
)
from .services import (
    StockUnderflowError,
    adjust_stock,
    create_stock,
    move_unit,
    reconcile_stock,
    resolve_effective_zone,
)

PENDING_IMPORT_SESSION_KEY = "lab_inventory_pending_import"
PENDING_IMPORT_MAX_AGE_SECONDS = 30 * 60


def healthz(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


@login_required
def home(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    items = CatalogItem.objects.none()
    units = PhysicalUnit.objects.none()
    zones = PlacementZone.objects.none()

    if query:
        items = CatalogItem.objects.filter(is_active=True).filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(part_number__icontains=query)
        )[:20]
        units = PhysicalUnit.objects.filter(is_active=True).filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(catalog_item__name__icontains=query)
            | Q(catalog_item__part_number__icontains=query)
        )[:20]
        zones = (
            PlacementZone.objects.filter(is_active=True)
            .filter(
                Q(code__icontains=query)
                | Q(name__icontains=query)
                | Q(fixture__code__icontains=query)
                | Q(fixture__name__icontains=query)
                | Q(fixture__room__name__icontains=query)
            )
            .select_related("fixture", "fixture__room")[:20]
        )

    return render(
        request,
        "inventory/home.html",
        {"query": query, "items": items, "units": units, "zones": zones},
    )


@login_required
def item_detail(request: HttpRequest, code: str) -> HttpResponse:
    item = get_object_or_404(CatalogItem, code=code)
    stocks = item.stocks.select_related("holder").all()
    total_stock = stocks.aggregate(total=Sum("quantity"))["total"]
    units = item.physical_units.all()
    return render(
        request,
        "inventory/item_detail.html",
        {"item": item, "stocks": stocks, "total_stock": total_stock, "units": units},
    )


@login_required
def unit_detail(request: HttpRequest, code: str) -> HttpResponse:
    unit = get_object_or_404(PhysicalUnit.objects.select_related("catalog_item"), code=code)
    try:
        placement = unit.placement
    except Placement.DoesNotExist:
        placement = None

    effective_zone = resolve_effective_zone(unit)
    stocks = unit.stocks.select_related("item").all()
    supported = unit.supported_placements.select_related("unit").order_by("order_key", "unit__code")
    recent_changes = unit.placement_changes.select_related(
        "from_zone", "from_support_unit", "to_zone", "to_support_unit", "actor"
    )[:10]

    return render(
        request,
        "inventory/unit_detail.html",
        {
            "unit": unit,
            "placement": placement,
            "effective_zone": effective_zone,
            "stocks": stocks,
            "supported": supported,
            "recent_changes": recent_changes,
        },
    )


@login_required
def zone_detail(request: HttpRequest, code: str) -> HttpResponse:
    zone = get_object_or_404(
        PlacementZone.objects.select_related("fixture", "fixture__room"),
        code=code,
    )
    placements = zone.placements.select_related("unit").order_by("order_key", "unit__code")
    return render(
        request,
        "inventory/zone_detail.html",
        {"zone": zone, "placements": placements},
    )


@login_required
@permission_required("inventory.change_stock", raise_exception=True)
def stock_adjust(request: HttpRequest, stock_id) -> HttpResponse:
    stock = get_object_or_404(Stock.objects.select_related("item", "holder"), pk=stock_id)
    form = StockAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            change = adjust_stock(
                stock=stock,
                delta=form.signed_delta(),
                reason=form.cleaned_data["reason"],
                note=form.cleaned_data["note"],
                actor=request.user,
            )
        except StockUnderflowError as exc:
            form.add_error("quantity", exc.messages[0])
        else:
            messages.success(
                request,
                f"{stock.item.name}: {change.resulting_quantity} {stock.item.unit} に更新しました。",
            )
            return redirect("inventory:unit-detail", code=stock.holder.code)

    return render(request, "inventory/stock_adjust.html", {"stock": stock, "form": form})


@login_required
@permission_required("inventory.change_stock", raise_exception=True)
def stock_count(request: HttpRequest, stock_id) -> HttpResponse:
    stock = get_object_or_404(Stock.objects.select_related("item", "holder"), pk=stock_id)
    form = StockCountForm(request.POST or None, initial={"counted_quantity": stock.quantity})
    if request.method == "POST" and form.is_valid():
        change = reconcile_stock(
            stock=stock,
            counted_quantity=form.cleaned_data["counted_quantity"],
            note=form.cleaned_data["note"],
            actor=request.user,
        )
        messages.success(
            request,
            f"棚卸を記録しました。補正量 {change.delta}, 現在 {change.resulting_quantity} {stock.item.unit}。",
        )
        return redirect("inventory:unit-detail", code=stock.holder.code)

    return render(request, "inventory/stock_count.html", {"stock": stock, "form": form})


@login_required
@permission_required("inventory.add_stock", raise_exception=True)
def stock_create(request: HttpRequest, code: str) -> HttpResponse:
    holder = get_object_or_404(PhysicalUnit, code=code)
    form = StockCreateForm(request.POST or None, holder=holder)
    if request.method == "POST" and form.is_valid():
        stock, _ = create_stock(
            item=form.cleaned_data["item"],
            holder=holder,
            initial_quantity=form.cleaned_data["initial_quantity"],
            reason=StockChange.Reason.COUNT,
            note=form.cleaned_data["note"],
            actor=request.user,
        )
        messages.success(request, f"{stock.item.name} の在庫管理を開始しました。")
        return redirect("inventory:unit-detail", code=holder.code)

    return render(request, "inventory/stock_create.html", {"holder": holder, "form": form})


@login_required
@permission_required("inventory.change_placement", raise_exception=True)
def unit_move(request: HttpRequest, code: str) -> HttpResponse:
    unit = get_object_or_404(PhysicalUnit, code=code)
    initial = {"target_type": MoveUnitForm.TargetType.ZONE, "order_key": 100}
    try:
        current = unit.placement
    except Placement.DoesNotExist:
        current = None

    if current:
        initial["order_key"] = current.order_key
        if current.zone_id:
            initial.update({"target_type": MoveUnitForm.TargetType.ZONE, "zone": current.zone_id})
        else:
            initial.update(
                {"target_type": MoveUnitForm.TargetType.SUPPORT, "support_unit": current.support_unit_id}
            )

    form = MoveUnitForm(request.POST or None, unit=unit, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            _, change = move_unit(
                unit=unit,
                zone=form.cleaned_data["zone"],
                support_unit=form.cleaned_data["support_unit"],
                order_key=form.cleaned_data["order_key"],
                note=form.cleaned_data["note"],
                actor=request.user,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            if change is None:
                messages.info(request, "配置に変更はありません。")
            else:
                messages.success(request, "通常保管位置を更新しました。")
            return redirect("inventory:unit-detail", code=unit.code)

    return render(request, "inventory/unit_move.html", {"unit": unit, "form": form})


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
                "dimensions_mm": [
                    str(room.width_mm) if room.width_mm is not None else None,
                    str(room.depth_mm) if room.depth_mm is not None else None,
                    str(room.height_mm) if room.height_mm is not None else None,
                ],
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
                "dimensions_mm": [
                    str(fixture.width_mm) if fixture.width_mm is not None else None,
                    str(fixture.depth_mm) if fixture.depth_mm is not None else None,
                    str(fixture.height_mm) if fixture.height_mm is not None else None,
                ],
                "position_mm": [
                    str(fixture.x_mm) if fixture.x_mm is not None else None,
                    str(fixture.y_mm) if fixture.y_mm is not None else None,
                    str(fixture.z_mm) if fixture.z_mm is not None else None,
                ],
                "rotation_z_deg": str(fixture.rotation_z_deg) if fixture.rotation_z_deg is not None else None,
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
                "dimensions_mm": [
                    str(zone.width_mm) if zone.width_mm is not None else None,
                    str(zone.depth_mm) if zone.depth_mm is not None else None,
                    str(zone.height_mm) if zone.height_mm is not None else None,
                ],
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
                "minimum_stock": str(item.minimum_stock) if item.minimum_stock is not None else None,
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
                "dimensions_mm": [
                    str(unit.width_mm) if unit.width_mm is not None else None,
                    str(unit.depth_mm) if unit.depth_mm is not None else None,
                    str(unit.height_mm) if unit.height_mm is not None else None,
                ],
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
