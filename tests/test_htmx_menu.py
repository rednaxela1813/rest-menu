"""Inline (HTMX) menu interactions: config fragment + add-to-cart fragment."""
import pytest
from django.urls import reverse

from tests import factories

pytestmark = pytest.mark.django_db

HX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def burger(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    return factories.MenuItemFactory(restaurant=restaurant, category=category)


def test_item_config_returns_form_fragment(client, burger):
    resp = client.get(reverse("menu:item_config", args=[burger.public_id]), **HX)
    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'class="cfg"' in body
    assert "<html" not in body  # fragment only, no base layout


def test_htmx_add_returns_confirmation_and_oob_badge(client, restaurant, table, burger):
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    resp = client.post(
        reverse("orders:cart_add"),
        {"menu_item_id": burger.id, "quantity": 2},
        **HX,
    )
    assert resp.status_code == 200
    assert resp["HX-Trigger"] == "itemAdded"
    body = resp.content.decode()
    assert "Pridané do košíka" in body
    # Out-of-band swap updates the floating cart badge to the new count (2).
    assert 'id="cart-fab-count"' in body
    assert 'hx-swap-oob="true"' in body
    assert ">2<" in body


def test_htmx_add_invalid_modifiers_returns_error_fragment(client, restaurant, table, burger):
    group = factories.ModifierGroupFactory(min_selections=0, max_selections=1)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)
    o1 = factories.ModifierOptionFactory(group=group)
    o2 = factories.ModifierOptionFactory(group=group)
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    resp = client.post(
        reverse("orders:cart_add"),
        {"menu_item_id": burger.id, "quantity": 1, "options": [o1.id, o2.id]},
        **HX,
    )
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "cfg__error" in body
    assert "Skúsiť znova" in body
