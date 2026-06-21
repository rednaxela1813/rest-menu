from django.urls import path

from . import views

app_name = "tables"

urlpatterns = [
    path("table/<int:number>/<uuid:token>/", views.table_menu, name="table_menu"),
    path("staff/tables/<int:pk>/qr.png", views.table_qr_png, name="qr_png"),
    path("staff/tables/qr.pdf", views.tables_qr_pdf, name="qr_pdf"),
]
