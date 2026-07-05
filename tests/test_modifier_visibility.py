"""Each modifier group renders as its own accordion (open or collapsed)."""
import pytest
from django.urls import reverse

from tests import factories

pytestmark = pytest.mark.django_db

OPEN = '<details class="cfg__group" open>'
CLOSED = '<details class="cfg__group">'


@pytest.fixture
def burger(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    return factories.MenuItemFactory(restaurant=restaurant, category=category)


def _link(burger, group):
    return factories.MenuItemModifierGroupFactory(menu_item=burger, modifier_group=group)


def test_non_collapsed_group_renders_open_accordion(client, burger):
    drinks = factories.ModifierGroupFactory(name_sk="Nápoj", collapsed_by_default=False)
    factories.ModifierOptionFactory(group=drinks, name_sk="Kofola")
    _link(burger, drinks)

    body = client.get(reverse("menu:item_config", args=[burger.public_id])).content.decode()
    assert "Nápoj" in body
    assert OPEN in body


def test_collapsed_group_renders_closed_accordion(client, burger):
    remove = factories.ModifierGroupFactory(name_sk="Odobrať ingrediencie", collapsed_by_default=True)
    factories.ModifierOptionFactory(group=remove, name_sk="Bez cibule")
    _link(burger, remove)

    body = client.get(reverse("menu:item_config", args=[burger.public_id])).content.decode()
    assert "Odobrať ingrediencie" in body
    # Folded by default: a cfg__group <details> without the `open` attribute.
    assert CLOSED in body


def test_required_group_opens_even_if_collapsed_flag_set(client, burger):
    # A required group must always be expanded, never folded away.
    doneness = factories.ModifierGroupFactory(
        name_sk="Prepečenie", is_required=True, collapsed_by_default=True
    )
    factories.ModifierOptionFactory(group=doneness, name_sk="Medium", is_default=True)
    factories.MenuItemModifierGroupFactory(
        menu_item=burger, modifier_group=doneness, is_required=True
    )

    body = client.get(reverse("menu:item_config", args=[burger.public_id])).content.decode()
    assert "Prepečenie" in body
    assert OPEN in body
    assert CLOSED not in body


def test_single_groups_have_independent_field_names(client, burger):
    """Each SINGLE group must use its own field name (otherwise picking a drink
    deselects the fries because radios share one name)."""
    sides = factories.ModifierGroupFactory(name_sk="Príloha", selection_type="SINGLE")
    drinks = factories.ModifierGroupFactory(name_sk="Nápoj", selection_type="SINGLE")
    factories.ModifierOptionFactory(group=sides, name_sk="Hranolky")
    factories.ModifierOptionFactory(group=drinks, name_sk="Kofola")
    _link(burger, sides)
    _link(burger, drinks)

    body = client.get(reverse("menu:item_config", args=[burger.public_id])).content.decode()
    assert f'name="opt-{sides.id}"' in body
    assert f'name="opt-{drinks.id}"' in body


def test_can_add_fries_and_drink_together(client, restaurant, table, burger):
    sides = factories.ModifierGroupFactory(name_sk="Príloha", selection_type="SINGLE")
    drinks = factories.ModifierGroupFactory(name_sk="Nápoj", selection_type="SINGLE")
    fries = factories.ModifierOptionFactory(group=sides, name_sk="Hranolky")
    cola = factories.ModifierOptionFactory(group=drinks, name_sk="Kofola")
    _link(burger, sides)
    _link(burger, drinks)

    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    resp = client.post(
        reverse("orders:cart_add"),
        {
            "menu_item_id": burger.id,
            "quantity": 1,
            f"opt-{sides.id}": fries.id,
            f"opt-{drinks.id}": cola.id,
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    # Both selections must be stored on the single cart line.
    line = next(iter(client.session["cart"].values()))
    assert fries.id in line["option_ids"]
    assert cola.id in line["option_ids"]
