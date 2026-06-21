"""Money calculations: item price, modifier deltas, order totals (Decimal only)."""
from decimal import Decimal

import pytest

from apps.orders import services
from apps.orders.states import OrderSource
from tests import factories

pytestmark = pytest.mark.django_db


def _order_with(restaurant, item, *, quantity, option_ids=None):
    return services.create_order(
        restaurant=restaurant,
        source=OrderSource.QR,
        items=[{"menu_item_id": item.id, "quantity": quantity, "comment": "", "option_ids": option_ids or []}],
    )


def test_line_total_without_modifiers(restaurant, burger):
    burger.price = Decimal("8.50")
    burger.save()
    order = _order_with(restaurant, burger, quantity=3)
    line = order.items.first()
    assert line.unit_price == Decimal("8.50")
    assert line.line_total == Decimal("25.50")
    assert order.total == Decimal("25.50")


def test_modifier_price_delta_added_to_unit_price(restaurant, burger):
    group = factories.ModifierGroupFactory(max_selections=3)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)
    cheese = factories.ModifierOptionFactory(group=group, price_delta=Decimal("1.00"))
    bacon = factories.ModifierOptionFactory(group=group, price_delta=Decimal("1.50"))

    order = _order_with(restaurant, burger, quantity=2, option_ids=[cheese.id, bacon.id])
    line = order.items.first()
    # 8.00 base + 1.00 + 1.50 = 10.50 per unit; x2 = 21.00
    assert line.unit_price == Decimal("10.50")
    assert line.line_total == Decimal("21.00")
    assert order.total == Decimal("21.00")


def test_totals_use_decimal_not_float(restaurant, burger):
    order = _order_with(restaurant, burger, quantity=1)
    assert isinstance(order.total, Decimal)
    assert isinstance(order.items.first().unit_price, Decimal)


def test_order_total_is_sum_of_lines(restaurant, burger, category):
    other = factories.MenuItemFactory(restaurant=restaurant, category=category, price=Decimal("3.20"))
    order = services.create_order(
        restaurant=restaurant,
        source=OrderSource.QR,
        items=[
            {"menu_item_id": burger.id, "quantity": 1, "comment": "", "option_ids": []},
            {"menu_item_id": other.id, "quantity": 2, "comment": "", "option_ids": []},
        ],
    )
    assert order.total == Decimal("8.00") + Decimal("6.40")
