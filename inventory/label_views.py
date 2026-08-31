from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import qrcode
import qrcode.image.svg

from .models import PhysicalUnit, PlacementZone

LABEL_SIZES = {
    "small": {"label": "45 × 25 mm", "width_mm": 45, "height_mm": 25},
    "medium": {"label": "60 × 35 mm", "width_mm": 60, "height_mm": 35},
    "large": {"label": "80 × 45 mm", "width_mm": 80, "height_mm": 45},
}
MAX_LABELS_PER_SHEET = 200


def _qr_svg(data: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
        image_factory=qrcode.image.svg.SvgPathImage,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image()
    return image.to_string(encoding="unicode")


def _qr_response(request: HttpRequest, target_path: str) -> HttpResponse:
    target_url = request.build_absolute_uri(target_path)
    response = HttpResponse(_qr_svg(target_url), content_type="image/svg+xml; charset=utf-8")
    response["Cache-Control"] = "private, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def unit_qr(request: HttpRequest, code: str) -> HttpResponse:
    unit = get_object_or_404(PhysicalUnit, code=code, is_active=True)
    return _qr_response(request, reverse("inventory:unit-detail", args=[unit.code]))


@login_required
def zone_qr(request: HttpRequest, code: str) -> HttpResponse:
    zone = get_object_or_404(PlacementZone, code=code, is_active=True)
    return _qr_response(request, reverse("inventory:zone-detail", args=[zone.code]))


@login_required
def labels_index(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    units = PhysicalUnit.objects.filter(is_active=True)
    zones = PlacementZone.objects.filter(
        is_active=True,
        fixture__is_active=True,
        fixture__room__is_active=True,
    ).select_related("fixture", "fixture__room")

    if query:
        units = units.filter(Q(code__icontains=query) | Q(name__icontains=query))
        zones = zones.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(fixture__code__icontains=query)
            | Q(fixture__name__icontains=query)
            | Q(fixture__room__name__icontains=query)
        )

    return render(
        request,
        "inventory/labels_index.html",
        {
            "query": query,
            "units": units.order_by("code")[:200],
            "zones": zones.order_by("fixture__room__code", "fixture__code", "level_order", "code")[:200],
            "label_sizes": LABEL_SIZES,
        },
    )


@login_required
def labels_print(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("inventory:labels")

    selected_units = list(dict.fromkeys(request.POST.getlist("unit")))
    selected_zones = list(dict.fromkeys(request.POST.getlist("zone")))
    total = len(selected_units) + len(selected_zones)
    if total == 0:
        messages.error(request, "印刷するラベルを1件以上選択してください。")
        return redirect("inventory:labels")
    if total > MAX_LABELS_PER_SHEET:
        messages.error(request, f"1回に印刷できるラベルは{MAX_LABELS_PER_SHEET}件までです。")
        return redirect("inventory:labels")

    size_key = request.POST.get("size", "medium")
    size = LABEL_SIZES.get(size_key, LABEL_SIZES["medium"])

    unit_by_code = {
        unit.code: unit
        for unit in PhysicalUnit.objects.filter(code__in=selected_units, is_active=True)
    }
    zone_by_code = {
        zone.code: zone
        for zone in PlacementZone.objects.filter(
            code__in=selected_zones,
            is_active=True,
            fixture__is_active=True,
            fixture__room__is_active=True,
        ).select_related("fixture", "fixture__room")
    }

    labels: list[dict] = []
    for code in selected_zones:
        zone = zone_by_code.get(code)
        if zone is None:
            continue
        labels.append(
            {
                "type": "zone",
                "code": zone.code,
                "name": zone.name,
                "category": "Placement Zone",
                "qr_url": reverse("inventory:zone-qr", args=[zone.code]),
            }
        )
    for code in selected_units:
        unit = unit_by_code.get(code)
        if unit is None:
            continue
        labels.append(
            {
                "type": "unit",
                "code": unit.code,
                "name": unit.name,
                "category": unit.get_kind_display(),
                "qr_url": reverse("inventory:unit-qr", args=[unit.code]),
            }
        )

    if not labels:
        messages.error(request, "選択された有効な対象が見つかりませんでした。")
        return redirect("inventory:labels")

    base_url = request.build_absolute_uri("/")
    non_production_host = request.get_host().split(":", 1)[0] in {"localhost", "127.0.0.1"}
    return render(
        request,
        "inventory/labels_print.html",
        {
            "labels": labels,
            "size": size,
            "base_url": base_url,
            "non_production_host": non_production_host,
        },
    )
