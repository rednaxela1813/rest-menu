"""Read-only queries for cashier / kitchen boards and history."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from .models import Order
from .states import OrderStatus


def status_chip_visible(order: Order | None, reset_minutes: int) -> bool:
    """Whether the guest status chip should still be shown.

    Open orders always show. Closed orders (served/cancelled/rejected) keep
    showing for ``reset_minutes`` after closure, then disappear and reset.
    """
    if order is None:
        return False
    if not order.is_closed:
        return True
    reference = order.served_at or order.cancelled_at or order.updated_at
    if reference is None:
        return True
    return timezone.now() - reference < timedelta(minutes=reset_minutes)

_BASE_PREFETCH = ("items__modifiers", "table")


def _base() -> QuerySet[Order]:
    return Order.objects.select_related("table", "restaurant").prefetch_related("items__modifiers")


def cashier_board(restaurant_id: int) -> dict[str, QuerySet[Order]]:
    qs = _base().filter(restaurant_id=restaurant_id)
    return {
        "new": qs.filter(status=OrderStatus.NEW),
        "confirmed": qs.filter(status=OrderStatus.CONFIRMED),
        "in_preparation": qs.filter(status=OrderStatus.IN_PREPARATION),
        "ready": qs.filter(status=OrderStatus.READY),
        "served": qs.filter(status=OrderStatus.SERVED).order_by("-served_at")[:25],
    }


def kitchen_queue(restaurant_id: int) -> dict[str, QuerySet[Order]]:
    qs = _base().filter(restaurant_id=restaurant_id)
    return {
        "waiting": qs.filter(status=OrderStatus.CONFIRMED).order_by("created_at"),
        "in_preparation": qs.filter(status=OrderStatus.IN_PREPARATION).order_by("preparation_started_at"),
        "ready": qs.filter(status=OrderStatus.READY).order_by("-ready_at")[:20],
    }


def order_history(restaurant_id: int, limit: int = 100) -> QuerySet[Order]:
    return _base().filter(restaurant_id=restaurant_id).order_by("-created_at")[:limit]


def get_for_staff(public_id) -> Order:
    return _base().get(public_id=public_id)
