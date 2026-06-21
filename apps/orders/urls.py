from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/items/", views.cart_add, name="cart_add"),
    path("cart/items/<str:line_id>/update/", views.cart_update, name="cart_update"),
    path("cart/items/<str:line_id>/remove/", views.cart_remove, name="cart_remove"),
    path("orders/", views.order_create, name="order_create"),
    path("orders/<uuid:public_id>/status/", views.order_status, name="order_status"),
    path("orders/<uuid:public_id>/chip/", views.order_chip, name="order_chip"),
]
