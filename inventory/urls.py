from django.urls import path

from . import bulk_views, label_views, scene_views, views

app_name = "inventory"

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("", views.home, name="home"),
    path("3d/", scene_views.room_3d, name="room-3d"),
    path("labels/", label_views.labels_index, name="labels"),
    path("labels/print/", label_views.labels_print, name="labels-print"),
    path("qr/u/<str:code>.svg", label_views.unit_qr, name="unit-qr"),
    path("qr/z/<str:code>.svg", label_views.zone_qr, name="zone-qr"),
    path("i/<str:code>/", views.item_detail, name="item-detail"),
    path("u/<str:code>/", views.unit_detail, name="unit-detail"),
    path("u/<str:code>/move/", views.unit_move, name="unit-move"),
    path("u/<str:code>/stock/add/", views.stock_create, name="stock-create"),
    path("z/<str:code>/", views.zone_detail, name="zone-detail"),
    path("stock/<uuid:stock_id>/adjust/", views.stock_adjust, name="stock-adjust"),
    path("stock/<uuid:stock_id>/count/", views.stock_count, name="stock-count"),
    path("import/", bulk_views.structured_import, name="structured-import"),
    path("import/confirm/", bulk_views.structured_import_confirm, name="structured-import-confirm"),
    path("export/snapshot.json", bulk_views.export_snapshot, name="export-snapshot"),
]
