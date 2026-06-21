from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("menu/", views.guest_menu, name="guest_menu"),
    path("menu/category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("menu/item/<uuid:public_id>/", views.item_detail, name="item_detail"),
    path("menu/item/<uuid:public_id>/config/", views.item_config, name="item_config"),
]
