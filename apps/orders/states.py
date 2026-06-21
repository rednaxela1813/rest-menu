"""Order status finite-state machine."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class OrderStatus(models.TextChoices):
    NEW = "new", _("Nová")
    CONFIRMED = "confirmed", _("Potvrdená")
    IN_PREPARATION = "in_preparation", _("Pripravuje sa")
    READY = "ready", _("Pripravená")
    SERVED = "served", _("Vydaná")
    CANCELLED = "cancelled", _("Zrušená")
    REJECTED = "rejected", _("Zamietnutá")


class OrderSource(models.TextChoices):
    QR = "qr", "QR"
    TABLET = "tablet", "Tablet"
    CASHIER = "cashier", _("Pokladňa")
    WAITER = "waiter", _("Čašník")


# Allowed transitions. Any change not listed here is rejected.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.NEW: {OrderStatus.CONFIRMED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
    OrderStatus.IN_PREPARATION: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.SERVED, OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
    OrderStatus.SERVED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REJECTED: set(),
}

# Statuses in which the order composition may still be edited.
EDITABLE_STATUSES = {OrderStatus.NEW, OrderStatus.CONFIRMED}
CLOSED_STATUSES = {OrderStatus.SERVED, OrderStatus.CANCELLED, OrderStatus.REJECTED}

# Guest-facing status text (Slovak).
GUEST_STATUS_TEXT: dict[str, str] = {
    OrderStatus.NEW: "Objednávka bola odoslaná",
    OrderStatus.CONFIRMED: "Objednávka bola prijatá",
    OrderStatus.IN_PREPARATION: "Objednávka sa pripravuje",
    OrderStatus.READY: "Objednávka je pripravená",
    OrderStatus.SERVED: "Objednávka bola vydaná",
    OrderStatus.REJECTED: "Objednávka bola zamietnutá",
    OrderStatus.CANCELLED: "Objednávka bola zrušená",
}


class InvalidStatusTransition(Exception):
    """Raised when a status change is not permitted by the state machine."""

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Neplatný prechod stavu: {current} → {target}")


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())
