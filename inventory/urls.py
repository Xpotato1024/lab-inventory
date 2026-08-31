from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("", views.home, name="home"),
]
