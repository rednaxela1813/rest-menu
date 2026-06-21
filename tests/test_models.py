"""Model constraints and invariants."""
import pytest
from django.db import IntegrityError

from apps.orders import services
from apps.orders.numbering import next_order_number, short_display_number
from apps.orders.states import OrderSource
from tests import factories

pytestmark = pytest.mark.django_db


def test_qr_token_is_unique_and_random():
    t1 = factories.DiningTableFactory()
    t2 = factories.DiningTableFactory()
    assert t1.qr_token != t2.qr_token


def test_table_number_unique_per_restaurant(restaurant):
    factories.DiningTableFactory(restaurant=restaurant, number=5)
    with pytest.raises(IntegrityError):
        factories.DiningTableFactory(restaurant=restaurant, number=5)


def test_regenerate_token_changes_value():
    table = factories.DiningTableFactory()
    old = table.qr_token
    table.regenerate_token()
    assert table.qr_token != old


def test_order_number_is_unique(restaurant, burger):
    o1 = services.create_order(
        restaurant=restaurant, source=OrderSource.QR,
        items=[{"menu_item_id": burger.id, "quantity": 1, "comment": "", "option_ids": []}],
    )
    o2 = services.create_order(
        restaurant=restaurant, source=OrderSource.QR,
        items=[{"menu_item_id": burger.id, "quantity": 1, "comment": "", "option_ids": []}],
    )
    assert o1.order_number != o2.order_number


def test_order_number_format():
    number = next_order_number()
    date_part, seq = number.split("-")
    assert len(date_part) == 8
    assert len(seq) == 4


def test_short_display_number():
    assert short_display_number("20260621-0124") == "#124"
