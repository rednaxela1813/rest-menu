from django.urls import path

from . import views

app_name = "kitchen"

urlpatterns = [
    path("orders/", views.board, name="board"),
    path("orders/<uuid:public_id>/start/", views.start, name="start"),
    path("orders/<uuid:public_id>/ready/", views.ready, name="ready"),
    path("orders/<uuid:public_id>/back/", views.back_to_preparation, name="back"),
]
