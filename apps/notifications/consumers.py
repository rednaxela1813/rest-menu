"""WebSocket consumers for cashier, kitchen and per-order guest updates."""
from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .groups import cashier_group, kitchen_group, order_group


class _BaseEventConsumer(AsyncJsonWebsocketConsumer):
    group_name: str = ""

    async def connect(self) -> None:
        if not self.group_name:
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code) -> None:
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_event(self, content: dict) -> None:
        """Handler for messages sent with ``{"type": "order.event", ...}``."""
        await self.send_json(content)


class CashierConsumer(_BaseEventConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if not (user and user.is_authenticated and getattr(user, "is_cashier", False)):
            await self.close()
            return
        restaurant_id = self.scope["url_route"]["kwargs"]["restaurant_id"]
        self.group_name = cashier_group(restaurant_id)
        await super().connect()


class KitchenConsumer(_BaseEventConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if not (user and user.is_authenticated and getattr(user, "is_kitchen", False)):
            await self.close()
            return
        restaurant_id = self.scope["url_route"]["kwargs"]["restaurant_id"]
        self.group_name = kitchen_group(restaurant_id)
        await super().connect()


class OrderStatusConsumer(_BaseEventConsumer):
    """Public per-order channel for guests watching their status page."""

    async def connect(self) -> None:
        order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.group_name = order_group(order_id)
        await super().connect()
