"""Order service layer: creation, snapshots, idempotency, optimistic locking."""
from decimal import Decimal

import pytest

from apps.orders import services
from apps.orders.models import Order
from apps.orders.services import (
    OrderConflictError,
    OrderValidationError,
    create_order,
)
from apps.orders.states import OrderSource, OrderStatus
from tests import factories

pytestmark = pytest.mark.django_db


def _items(item, qty=1, options=None):
    return [{"menu_item_id": item.id, "quantity": qty, "comment": "", "option_ids": options or []}]


def test_create_order_is_atomic_and_sets_number(restaurant, burger):
    order = create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger))
    assert order.order_number
    assert order.status == OrderStatus.NEW
    assert order.items.count() == 1


def test_snapshot_preserves_name_and_price(restaurant, burger):
    order = create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger))
    line = order.items.first()
    # Change menu after ordering — snapshot must not move.
    burger.name_sk = "Premenovaný"
    burger.price = Decimal("99.00")
    burger.save()
    line.refresh_from_db()
    assert line.item_name_snapshot != "Premenovaný"
    assert line.unit_price == Decimal("8.00")


def test_idempotency_key_prevents_duplicates(restaurant, burger):
    o1 = create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger), idempotency_key="abc")
    o2 = create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger), idempotency_key="abc")
    assert o1.pk == o2.pk
    assert Order.objects.count() == 1


def test_cannot_order_unavailable_item(restaurant, burger):
    burger.is_available = False
    burger.save()
    with pytest.raises(OrderValidationError):
        create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger))


def test_empty_order_rejected(restaurant):
    with pytest.raises(OrderValidationError):
        create_order(restaurant=restaurant, source=OrderSource.QR, items=[])


def test_required_modifier_enforced(restaurant, burger):
    group = factories.ModifierGroupFactory(min_selections=1, max_selections=1, is_required=True)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group, is_required=True)
    factories.ModifierOptionFactory(group=group)
    with pytest.raises(OrderValidationError):
        create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger))


def test_max_selections_enforced(restaurant, burger):
    group = factories.ModifierGroupFactory(min_selections=0, max_selections=1)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)
    o1 = factories.ModifierOptionFactory(group=group)
    o2 = factories.ModifierOptionFactory(group=group)
    with pytest.raises(OrderValidationError):
        create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger, options=[o1.id, o2.id]))


def test_modifier_snapshots_saved(restaurant, burger):
    group = factories.ModifierGroupFactory(max_selections=3)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)
    opt = factories.ModifierOptionFactory(group=group, name_sk="Extra syr", price_delta=Decimal("1.00"))
    order = create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger, options=[opt.id]))
    mod = order.items.first().modifiers.first()
    assert mod.option_name_snapshot == "Extra syr"
    assert mod.price_delta == Decimal("1.00")
    assert mod.total_delta == Decimal("1.00")


def test_optimistic_locking_blocks_stale_version(restaurant, burger, cashier):
    order = create_order(restaurant=restaurant, source=OrderSource.QR, items=_items(burger))
    stale_version = order.version
    services.confirm_order(order, user=cashier, expected_version=stale_version)
    # A second actor still holding the old version must be rejected.
    with pytest.raises(OrderConflictError):
        services.start_order_preparation(order, user=cashier, expected_version=stale_version)
