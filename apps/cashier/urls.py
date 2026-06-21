from django.urls import path

from . import views

app_name = "cashier"

urlpatterns = [
    path("orders/", views.board, name="board"),
    path("orders/<uuid:public_id>/", views.order_detail, name="order_detail"),
    path("orders/<uuid:public_id>/confirm/", views.confirm, name="confirm"),
    path("orders/<uuid:public_id>/reject/", views.reject, name="reject"),
    path("orders/<uuid:public_id>/cancel/", views.cancel, name="cancel"),
    path("orders/<uuid:public_id>/serve/", views.serve, name="serve"),
]
