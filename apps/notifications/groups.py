"""WebSocket group-name helpers."""
from __future__ import annotations


def cashier_group(restaurant_id: int) -> str:
    return f"restaurant_{restaurant_id}_cashier"


def kitchen_group(restaurant_id: int) -> str:
    return f"restaurant_{restaurant_id}_kitchen"


def order_group(order_id) -> str:
    return f"order_{order_id}"
