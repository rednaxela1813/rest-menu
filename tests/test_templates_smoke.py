"""Smoke tests: guest-facing pages render (catch template errors)."""
import pytest
from django.urls import reverse

from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def menu(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    factories.MenuItemFactory(restaurant=restaurant, category=category, is_featured=True)
    return category


def test_guest_menu_renders(client, restaurant, menu):
    resp = client.get(reverse("menu:guest_menu"))
    assert resp.status_code == 200
    assert restaurant.name.encode() in resp.content


def test_item_detail_renders(client, restaurant, menu):
    item = factories.MenuItemFactory(restaurant=restaurant, category=menu)
    resp = client.get(reverse("menu:item_detail", args=[item.public_id]))
    assert resp.status_code == 200


def test_cart_and_status_render(client, restaurant, table, menu):
    item = factories.MenuItemFactory(restaurant=restaurant, category=menu)
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    client.post(reverse("orders:cart_add"), {"menu_item_id": item.id, "quantity": 1})

    cart_resp = client.get(reverse("orders:cart_detail"))
    assert cart_resp.status_code == 200

    order_resp = client.post(reverse("orders:order_create"), {}, follow=True)
    assert order_resp.status_code == 200
    # Guest status text "Objednávka bola odoslaná".
    assert "Objednávka bola odoslaná" in order_resp.content.decode()
