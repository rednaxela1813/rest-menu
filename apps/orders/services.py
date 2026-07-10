"""Order business logic. All status changes flow through here, never views."""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.menu.models import MenuItem, ModifierGroup, ModifierOption
from apps.menu.services import check_modifier_selection
from apps.restaurants.models import Restaurant

from .models import Order, OrderItem, OrderItemModifier, OrderStatusHistory
from .numbering import next_order_number
from .states import (
    EDITABLE_STATUSES,
    InvalidStatusTransition,
    OrderStatus,
    can_transition,
)

logger = logging.getLogger("orders")


class OrderConflictError(Exception):
    """Raised when optimistic locking detects a concurrent modification."""


class OrderValidationError(Exception):
    """Raised when an order cannot be created/edited due to business rules."""


# --- Creation -------------------------------------------------------------
@transaction.atomic
def create_order(
    *,
    restaurant: Restaurant,
    table=None,
    source: str,
    items: list[dict],
    customer_comment: str = "",
    created_by=None,
    idempotency_key: str | None = None,
) -> Order:
    """Create an order atomically from validated cart payload.

    ``items`` is a list of dicts: ``{menu_item_id, quantity, comment, option_ids}``.
    Snapshots of names and prices are stored so history is immutable.
    """
    if not items:
        raise OrderValidationError("Objednávka neobsahuje žiadne položky.")

    # Idempotency: a repeated submit with the same key returns the same order.
    if idempotency_key:
        existing = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            logger.info("Idempotent replay for key=%s -> order %s", idempotency_key, existing.order_number)
            return existing

    order = Order.objects.create(
        order_number=next_order_number(),
        restaurant=restaurant,
        table=table,
        status=OrderStatus.NEW,
        source=source,
        customer_comment=customer_comment.strip(),
        currency=restaurant.currency,
        created_by=created_by,
        idempotency_key=idempotency_key,
    )

    for raw in items:
        menu_item = MenuItem.objects.get(id=raw["menu_item_id"])
        if not menu_item.can_be_ordered:
            raise OrderValidationError(f"Položka „{menu_item.name}“ nie je dostupná.")

        option_ids = [int(o) for o in raw.get("option_ids", [])]
        menu_item_modifiers = raw.get("menu_item_modifiers", [])
        _validate_modifiers(menu_item, option_ids, menu_item_modifiers)

        order_item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            item_name_snapshot=menu_item.name,
            unit_price=menu_item.price,
            quantity=int(raw["quantity"]),
            customer_comment=raw.get("comment", "").strip(),
            status=OrderStatus.NEW,
        )

        options = ModifierOption.objects.filter(id__in=option_ids, is_active=True).select_related(
            "group"
        )
        for opt in options:
            OrderItemModifier.objects.create(
                order_item=order_item,
                modifier_option=opt,
                group_name_snapshot=opt.group.name,
                option_name_snapshot=opt.name,
                price_delta=opt.price_delta,
                quantity=1,
            )
        menu_option_groups = {
            group.id: group
            for group in ModifierGroup.objects.filter(
                id__in=[raw_item["group_id"] for raw_item in menu_item_modifiers]
            )
        }
        menu_option_items = {
            option_item.id: option_item
            for option_item in MenuItem.objects.filter(
                id__in=[raw_item["menu_item_id"] for raw_item in menu_item_modifiers]
            )
        }
        for raw_item in menu_item_modifiers:
            group = menu_option_groups[raw_item["group_id"]]
            option_item = menu_option_items[raw_item["menu_item_id"]]
            OrderItemModifier.objects.create(
                order_item=order_item,
                modifier_menu_item=option_item,
                group_name_snapshot=group.name,
                option_name_snapshot=option_item.name,
                price_delta=option_item.price,
                quantity=1,
            )
        order_item.recalculate()

    order.recalculate_totals()
    _record_history(order, previous="", new=OrderStatus.NEW, user=created_by, comment="Vytvorená")

    logger.info("Order %s created (source=%s, total=%s)", order.order_number, source, order.total)
    _notify(order, "order.created")
    return order


def _validate_modifiers(
    menu_item: MenuItem, option_ids: list[int], menu_item_modifiers: list[dict] | None = None
) -> None:
    error = check_modifier_selection(menu_item, option_ids, menu_item_modifiers)
    if error:
        raise OrderValidationError(error)


# --- State transitions ----------------------------------------------------
@transaction.atomic
def _transition(
    order: Order,
    target: str,
    *,
    user=None,
    comment: str = "",
    expected_version: int | None = None,
    timestamp_field: str | None = None,
) -> Order:
    # Lock the row and re-read to avoid lost updates.
    order = Order.objects.select_for_update().get(pk=order.pk)

    if expected_version is not None and order.version != expected_version:
        raise OrderConflictError(
            "Objednávku medzitým zmenil iný používateľ. Načítajte ju znova."
        )

    if not can_transition(order.status, target):
        raise InvalidStatusTransition(order.status, target)

    previous = order.status
    order.status = target
    order.version += 1
    update_fields = ["status", "version", "updated_at"]

    now = timezone.now()
    if timestamp_field:
        setattr(order, timestamp_field, now)
        update_fields.append(timestamp_field)
    if target == OrderStatus.CONFIRMED:
        order.confirmed_by = user
        update_fields.append("confirmed_by")
    if target in {OrderStatus.CANCELLED, OrderStatus.REJECTED}:
        order.cancelled_by = user
        order.cancelled_at = now
        update_fields += ["cancelled_by", "cancelled_at"]

    order.save(update_fields=update_fields)
    _record_history(order, previous=previous, new=target, user=user, comment=comment)
    logger.info("Order %s: %s -> %s by %s", order.order_number, previous, target, user)
    return order


def confirm_order(order: Order, *, user, expected_version: int | None = None) -> Order:
    order = _transition(
        order,
        OrderStatus.CONFIRMED,
        user=user,
        expected_version=expected_version,
        timestamp_field="confirmed_at",
    )
    _audit(user, "order.confirmed", order)
    _notify(order, "order.confirmed")
    return order


def reject_order(order: Order, *, user, comment: str = "", expected_version: int | None = None) -> Order:
    order = _transition(
        order, OrderStatus.REJECTED, user=user, comment=comment, expected_version=expected_version
    )
    _audit(user, "order.rejected", order, comment)
    _notify(order, "order.cancelled")
    return order


def cancel_order(order: Order, *, user, comment: str = "", expected_version: int | None = None) -> Order:
    order = _transition(
        order, OrderStatus.CANCELLED, user=user, comment=comment, expected_version=expected_version
    )
    _audit(user, "order.cancelled", order, comment)
    _notify(order, "order.cancelled")
    return order


def start_order_preparation(order: Order, *, user, expected_version: int | None = None) -> Order:
    order = _transition(
        order,
        OrderStatus.IN_PREPARATION,
        user=user,
        expected_version=expected_version,
        timestamp_field="preparation_started_at",
    )
    _notify(order, "order.preparation_started")
    return order


def mark_order_ready(order: Order, *, user, expected_version: int | None = None) -> Order:
    order = _transition(
        order,
        OrderStatus.READY,
        user=user,
        expected_version=expected_version,
        timestamp_field="ready_at",
    )
    _notify(order, "order.ready")
    return order


def return_to_preparation(order: Order, *, user, expected_version: int | None = None) -> Order:
    order = _transition(
        order, OrderStatus.IN_PREPARATION, user=user, expected_version=expected_version
    )
    _notify(order, "order.preparation_started")
    return order


def mark_order_served(order: Order, *, user, expected_version: int | None = None) -> Order:
    order = _transition(
        order,
        OrderStatus.SERVED,
        user=user,
        expected_version=expected_version,
        timestamp_field="served_at",
    )
    _notify(order, "order.served")
    return order


# --- Recalculation --------------------------------------------------------
@transaction.atomic
def recalculate_order(order: Order) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    for item in order.items.all():
        item.recalculate()
    order.recalculate_totals()
    return order


def assert_editable(order: Order) -> None:
    if order.status not in EDITABLE_STATUSES:
        raise OrderValidationError(
            "Túto objednávku už nie je možné upraviť bez administrátorského zásahu."
        )


# --- Helpers --------------------------------------------------------------
def _record_history(order: Order, *, previous: str, new: str, user, comment: str = "") -> None:
    OrderStatusHistory.objects.create(
        order=order, previous_status=previous, new_status=new, changed_by=user, comment=comment
    )


def _audit(user, action: str, order: Order, description: str = "") -> None:
    try:
        from apps.audit.services import record_action

        record_action(
            user=user,
            action=action,
            obj=order,
            description=description or f"Objednávka {order.order_number}",
        )
    except Exception:  # pragma: no cover - auditing must never break the flow
        logger.exception("Audit logging failed for %s", action)


def _notify(order: Order, event: str) -> None:
    try:
        from apps.notifications.events import broadcast_order_event

        broadcast_order_event(order, event)
    except Exception:  # pragma: no cover - realtime is best-effort, polling backs it up
        logger.exception("WebSocket broadcast failed for %s", event)
