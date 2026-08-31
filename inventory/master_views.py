from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .master_forms import CatalogItemForm, PhysicalUnitForm
from .models import CatalogItem, PhysicalUnit


@login_required
@permission_required("inventory.view_catalogitem", raise_exception=True)
def master_index(request):
    query = request.GET.get("q", "").strip()
    items = CatalogItem.objects.all()
    units = PhysicalUnit.objects.select_related("catalog_item").all()

    if query:
        items = items.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(part_number__icontains=query)
        )
        units = units.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(catalog_item__code__icontains=query)
            | Q(catalog_item__name__icontains=query)
        )

    return render(
        request,
        "inventory/master_index.html",
        {
            "query": query,
            "items": items.order_by("code")[:250],
            "units": units.order_by("code")[:250],
        },
    )


@login_required
@permission_required("inventory.add_catalogitem", raise_exception=True)
def item_create(request):
    form = CatalogItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"{item.code} — {item.name} を作成しました。")
        return redirect("inventory:master")
    return render(
        request,
        "inventory/master_form.html",
        {"form": form, "title": "品目を追加", "entity_label": "Catalog Item"},
    )


@login_required
@permission_required("inventory.change_catalogitem", raise_exception=True)
def item_edit(request, code: str):
    item = get_object_or_404(CatalogItem, code=code)
    form = CatalogItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"{item.code} を更新しました。")
        return redirect("inventory:master")
    return render(
        request,
        "inventory/master_form.html",
        {"form": form, "title": f"{item.code} を編集", "entity_label": "Catalog Item"},
    )


@login_required
@permission_required("inventory.add_physicalunit", raise_exception=True)
def unit_create(request):
    form = PhysicalUnitForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        unit = form.save()
        messages.success(
            request,
            f"{unit.code} — {unit.name} を作成しました。必要なら通常保管位置を設定してください。",
        )
        return redirect("inventory:unit-detail", code=unit.code)
    return render(
        request,
        "inventory/master_form.html",
        {"form": form, "title": "箱・工具・機器を追加", "entity_label": "Physical Unit"},
    )


@login_required
@permission_required("inventory.change_physicalunit", raise_exception=True)
def unit_edit(request, code: str):
    unit = get_object_or_404(PhysicalUnit, code=code)
    form = PhysicalUnitForm(request.POST or None, instance=unit)
    if request.method == "POST" and form.is_valid():
        unit = form.save()
        messages.success(request, f"{unit.code} を更新しました。")
        return redirect("inventory:unit-detail", code=unit.code)
    return render(
        request,
        "inventory/master_form.html",
        {"form": form, "title": f"{unit.code} を編集", "entity_label": "Physical Unit"},
    )
