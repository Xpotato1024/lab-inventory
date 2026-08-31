from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import PlacementChange, StockChange


@login_required
def activity(request):
    query = request.GET.get("q", "").strip()

    stock_changes = StockChange.objects.select_related(
        "stock__item",
        "stock__holder",
        "actor",
    )
    placement_changes = PlacementChange.objects.select_related(
        "unit",
        "from_zone",
        "from_support_unit",
        "to_zone",
        "to_support_unit",
        "actor",
    )

    if query:
        stock_changes = stock_changes.filter(
            Q(stock__item__code__icontains=query)
            | Q(stock__item__name__icontains=query)
            | Q(stock__holder__code__icontains=query)
            | Q(stock__holder__name__icontains=query)
            | Q(actor__username__icontains=query)
            | Q(note__icontains=query)
        )
        placement_changes = placement_changes.filter(
            Q(unit__code__icontains=query)
            | Q(unit__name__icontains=query)
            | Q(from_zone__code__icontains=query)
            | Q(to_zone__code__icontains=query)
            | Q(from_support_unit__code__icontains=query)
            | Q(to_support_unit__code__icontains=query)
            | Q(actor__username__icontains=query)
            | Q(note__icontains=query)
        )

    return render(
        request,
        "inventory/activity.html",
        {
            "query": query,
            "stock_changes": stock_changes[:100],
            "placement_changes": placement_changes[:100],
        },
    )
