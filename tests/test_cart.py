"""Session cart validation and pricing."""
from decimal import Decimal

import pytest
from django.contrib.sessions.backends.db import SessionStore

from apps.orders.cart import Cart, CartError
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def session():
    return SessionStore()


def test_add_and_total(session, burger):
    cart = Cart(session)
    cart.add(menu_item_id=burger.id, quantity=2, comment="", option_ids=[])
    assert cart.count == 2
    assert cart.total == Decimal("16.00")


def test_cannot_add_unavailable_item(session, burger):
    burger.is_available = False
    burger.save()
    cart = Cart(session)
    with pytest.raises(CartError):
        cart.add(menu_item_id=burger.id, quantity=1, comment="", option_ids=[])


def test_quantity_must_be_positive(session, burger):
    cart = Cart(session)
    with pytest.raises(CartError):
        cart.add(menu_item_id=burger.id, quantity=0, comment="", option_ids=[])


def test_checkout_validation_flags_unavailable(session, burger):
    cart = Cart(session)
    cart.add(menu_item_id=burger.id, quantity=1, comment="", option_ids=[])
    burger.is_available = False
    burger.save()
    blocked = cart.validate_for_checkout()
    assert burger.name in blocked


def test_modifier_rules_validated_on_add(session, burger):
    group = factories.ModifierGroupFactory(min_selections=0, max_selections=1)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)
    o1 = factories.ModifierOptionFactory(group=group)
    o2 = factories.ModifierOptionFactory(group=group)
    cart = Cart(session)
    with pytest.raises(CartError):
        cart.add(menu_item_id=burger.id, quantity=1, comment="", option_ids=[o1.id, o2.id])


def test_remove_line(session, burger):
    cart = Cart(session)
    line_id = cart.add(menu_item_id=burger.id, quantity=1, comment="", option_ids=[])
    cart.remove(line_id)
    assert cart.is_empty()
