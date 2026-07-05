"""Nested modifier groups: a container (Nápoj) with subcategories (Pivo/Nealko)."""
import pytest
from django.urls import reverse

from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def burger(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    return factories.MenuItemFactory(restaurant=restaurant, category=category)


def _drink_tree(burger, *, container_max=0):
    """Container "Nápoj" → Pivo / Nealko, each pick-up-to-1. Returns the pieces."""
    container = factories.ModifierGroupFactory(
        name_sk="Nápoj", min_selections=0, max_selections=container_max
    )
    beer = factories.ModifierGroupFactory(
        name_sk="Pivo", parent=container, selection_type="SINGLE", min_selections=0, max_selections=1
    )
    soft = factories.ModifierGroupFactory(
        name_sk="Nealko", parent=container, selection_type="SINGLE", min_selections=0, max_selections=1
    )
    saris = factories.ModifierOptionFactory(group=beer, name_sk="Šariš")
    kofola = factories.ModifierOptionFactory(group=soft, name_sk="Kofola")
    factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=container)
    return container, beer, soft, saris, kofola


def _add(client, table, burger, payload):
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    return client.post(
        reverse("orders:cart_add"),
        {"menu_item_id": burger.id, "quantity": 1, **payload},
        HTTP_HX_REQUEST="true",
    )


def test_container_renders_nested_accordions(client, burger):
    container, beer, soft, saris, kofola = _drink_tree(burger)

    body = client.get(reverse("menu:item_config", args=[burger.public_id])).content.decode()
    # Container header and both subcategory headers are present.
    assert "Nápoj" in body and "Pivo" in body and "Nealko" in body
    # Options live under their leaf subgroup field names (not the container).
    assert f'name="opt-{beer.id}"' in body
    assert f'name="opt-{soft.id}"' in body
    assert f'name="opt-{container.id}"' not in body
    assert "Šariš" in body and "Kofola" in body


def test_subcategory_option_is_accepted(client, table, burger):
    container, beer, soft, saris, kofola = _drink_tree(burger)

    resp = _add(client, table, burger, {f"opt-{beer.id}": saris.id})
    assert resp.status_code == 200
    line = next(iter(client.session["cart"].values()))
    assert saris.id in line["option_ids"]


def test_independent_subcategories_allow_beer_and_soft_together(client, table, burger):
    # container_max=0 → no aggregate cap, so a beer AND a soft drink are allowed.
    container, beer, soft, saris, kofola = _drink_tree(burger, container_max=0)

    resp = _add(client, table, burger, {f"opt-{beer.id}": saris.id, f"opt-{soft.id}": kofola.id})
    assert resp.status_code == 200
    line = next(iter(client.session["cart"].values()))
    assert saris.id in line["option_ids"] and kofola.id in line["option_ids"]


def test_child_max_is_enforced(client, table, burger):
    container, beer, soft, saris, kofola = _drink_tree(burger)
    saris2 = factories.ModifierOptionFactory(group=beer, name_sk="Zlatý Bažant")

    # Two beers exceed the subcategory's max_selections=1 → rejected, cart stays empty.
    resp = _add(client, table, burger, {f"opt-{beer.id}": [saris.id, saris2.id]})
    assert resp.status_code == 200
    assert not client.session.get("cart")


def test_container_aggregate_cap_is_enforced(client, table, burger):
    # container_max=1 → at most one drink across all subcategories.
    container, beer, soft, saris, kofola = _drink_tree(burger, container_max=1)

    resp = _add(client, table, burger, {f"opt-{beer.id}": saris.id, f"opt-{soft.id}": kofola.id})
    assert resp.status_code == 200
    assert not client.session.get("cart")


def test_option_from_unlinked_subcategory_is_rejected(client, table, burger):
    container, beer, soft, saris, kofola = _drink_tree(burger)
    # A subgroup under a *different*, unlinked container must not be accepted.
    other = factories.ModifierGroupFactory(name_sk="Iné", max_selections=0)
    other_sub = factories.ModifierGroupFactory(name_sk="Cudzie", parent=other, max_selections=1)
    stray = factories.ModifierOptionFactory(group=other_sub, name_sk="Cudzí")

    resp = _add(client, table, burger, {f"opt-{other_sub.id}": stray.id})
    assert resp.status_code == 200
    assert not client.session.get("cart")
