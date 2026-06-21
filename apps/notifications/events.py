"""Broadcast order events to the relevant WebSocket groups."""
from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .groups import cashier_group, kitchen_group, order_group

logger = logging.getLogger("orders")

# Which channel groups should hear each event.
_CASHIER_EVENTS = {
    "order.created",
    "order.confirmed",
    "order.updated",
    "order.cancelled",
    "order.ready",
    "order.served",
}
_KITCHEN_EVENTS = {
    "order.confirmed",
    "order.updated",
    "order.cancelled",
    "order.preparation_started",
    "order.ready",
}


def broadcast_order_event(order, event: str) -> None:
    layer = get_channel_layer()
    if layer is None:  # No channel layer configured (e.g. some test runs).
        return

    payload = {
        "type": "order.event",
        "event": event,
        "order_id": str(order.public_id),
        "order_number": order.order_number,
        "status": order.status,
        "table": str(order.table) if order.table_id else None,
        "total": str(order.total),
    }

    targets = [order_group(order.public_id)]
    if event in _CASHIER_EVENTS:
        targets.append(cashier_group(order.restaurant_id))
    if event in _KITCHEN_EVENTS:
        targets.append(kitchen_group(order.restaurant_id))

    for group in targets:
        async_to_sync(layer.group_send)(group, payload)
    logger.debug("Broadcast %s to %s", event, targets)


def broadcast_menu_availability(item) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        "type": "order.event",
        "event": "menu.item_availability_changed",
        "item_id": str(item.public_id),
        "is_available": item.is_available,
    }
    async_to_sync(layer.group_send)(cashier_group(item.restaurant_id), payload)
