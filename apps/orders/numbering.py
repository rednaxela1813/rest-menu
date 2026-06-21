"""Daily order-number generation: ``YYYYMMDD-NNNN``."""
from __future__ import annotations

from django.utils import timezone

from .models import Order


def next_order_number() -> str:
    """Return the next sequential number for today.

    Must be called inside the order-creating ``transaction.atomic()`` block so
    the unique constraint on ``order_number`` serialises concurrent creators.
    """
    today = timezone.localdate()
    prefix = today.strftime("%Y%m%d")
    todays_count = Order.objects.filter(created_at__date=today).count()
    sequence = todays_count + 1
    return f"{prefix}-{sequence:04d}"


def short_display_number(order_number: str) -> str:
    """``20260621-0124`` -> ``#124`` for compact UI badges."""
    try:
        return f"#{int(order_number.split('-')[-1])}"
    except (ValueError, IndexError):
        return f"#{order_number}"
