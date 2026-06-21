from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/cashier/<int:restaurant_id>/", consumers.CashierConsumer.as_asgi()),
    path("ws/kitchen/<int:restaurant_id>/", consumers.KitchenConsumer.as_asgi()),
    path("ws/order/<uuid:order_id>/", consumers.OrderStatusConsumer.as_asgi()),
]
