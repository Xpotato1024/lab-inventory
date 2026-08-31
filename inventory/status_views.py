from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .status import low_stock_items


@login_required
def low_stock(request):
    items = list(low_stock_items().prefetch_related("stocks__holder"))
    return render(
        request,
        "inventory/low_stock.html",
        {"items": items},
    )
