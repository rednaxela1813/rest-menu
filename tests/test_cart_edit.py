"""Editing a cart line: pre-fill and replace-in-place."""
import pytest
from django.urls import reverse

from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def burger(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    return factories.MenuItemFactory(restaurant=restaurant, category=category)


def _add(client, table, burger, qty=1):
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    client.post(reverse("orders:cart_add"), {"menu_item_id": burger.id, "quantity": qty})
    return next(iter(client.session["cart"]))


def test_edit_link_prefills_quantity(client, restaurant, table, burger):
    line_id = _add(client, table, burger, qty=2)
    resp = client.get(reverse("menu:item_detail", args=[burger.public_id]) + f"?edit={line_id}")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert f'name="edit_line" value="{line_id}"' in body
    assert 'value="2"' in body  # quantity pre-filled
    assert "Uložiť zmeny" in body


def test_edit_replaces_line_not_duplicates(client, restaurant, table, burger):
    line_id = _add(client, table, burger, qty=1)
    resp = client.post(
        reverse("orders:cart_add"),
        {"menu_item_id": burger.id, "quantity": 4, "edit_line": line_id},
    )
    assert resp.status_code == 302
    assert resp.url == reverse("orders:cart_detail")
    cart = client.session["cart"]
    assert len(cart) == 1  # replaced, not duplicated
    assert line_id not in cart  # old line gone
    assert next(iter(cart.values()))["quantity"] == 4


def test_edit_changes_modifiers(client, restaurant, table, burger):
    group = factories.ModifierGroupFactory(selection_type="MULTIPLE", max_selections=3)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)
    cheese = factories.ModifierOptionFactory(group=group, name_sk="Extra syr")

    line_id = _add(client, table, burger, qty=1)
    client.post(
        reverse("orders:cart_add"),
        {"menu_item_id": burger.id, "quantity": 1, f"opt-{group.id}": cheese.id, "edit_line": line_id},
    )
    cart = client.session["cart"]
    assert len(cart) == 1
    assert cheese.id in next(iter(cart.values()))["option_ids"]


def test_invalid_edit_keeps_original_line(client, restaurant, table, burger):
    # Required group; submitting the edit without choosing it must fail and keep
    # the original line intact.
    group = factories.ModifierGroupFactory(min_selections=1, max_selections=1, is_required=True)
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group, is_required=True)
    factories.ModifierOptionFactory(group=group, name_sk="Medium")

    # Seed a line directly (bypassing validation) to simulate an existing line.
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    session = client.session
    session["cart"] = {"abc123": {"menu_item_id": burger.id, "quantity": 1, "comment": "", "option_ids": []}}
    session.save()

    resp = client.post(
        reverse("orders:cart_add"),
        {"menu_item_id": burger.id, "quantity": 2, "edit_line": "abc123"},
    )
    assert resp.status_code == 302  # back to item page with error
    cart = client.session["cart"]
    assert "abc123" in cart  # original NOT removed because the edit failed
