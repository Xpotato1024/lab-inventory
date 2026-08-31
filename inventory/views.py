from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MoveUnitForm, StockAdjustmentForm, StockCountForm, StockCreateForm
from .models import CatalogItem, PhysicalUnit, Placement, PlacementZone, Stock, StockChange
from .services import (
    StockUnderflowError,
    adjust_stock,
    create_stock,
    move_unit,
    reconcile_stock,
    resolve_effective_zone,
)


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
