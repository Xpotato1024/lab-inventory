from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def healthz(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "inventory/home.html")
