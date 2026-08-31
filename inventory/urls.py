from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("", views.home, name="home"),
    path("i/<str:code>/", views.item_detail, name="item-detail"),
    path("u/<str:code>/", views.unit_detail, name="unit-detail"),
    path("u/<str:code>/move/", views.unit_move, name="unit-move"),
    path("u/<str:code>/stock/add/", views.stock_create, name="stock-create"),
    path("z/<str:code>/", views.zone_detail, name="zone-detail"),
    path("stock/<uuid:stock_id>/adjust/", views.stock_adjust, name="stock-adjust"),
    path("stock/<uuid:stock_id>/count/", views.stock_count, name="stock-count"),
    path("import/", views.structured_import, name="structured-import"),
    path("import/confirm/", views.structured_import_confirm, name="structured-import-confirm"),
    path("export/snapshot.json", views.export_snapshot, name="export-snapshot"),
]
