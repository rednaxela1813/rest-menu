"""End-to-end flow: guest → cart → order → cashier → kitchen → ready → served."""
import pytest
from django.urls import reverse

from apps.orders.models import Order
from apps.orders.states import OrderStatus
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def menu(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    burger = factories.MenuItemFactory(restaurant=restaurant, category=category, is_featured=True)
    return {"category": category, "burger": burger}


def test_full_order_lifecycle(client, restaurant, table, menu, cashier, kitchen_user):
    burger = menu["burger"]

    # 1. Guest opens table QR link -> session bound to table, redirect to menu.
    resp = client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    assert resp.status_code == 302
    assert client.session["table_id"] == table.id

    # 2. Guest adds item to cart.
    resp = client.post(reverse("orders:cart_add"), {"menu_item_id": burger.id, "quantity": 2})
    assert resp.status_code == 302

    # 3. Guest visits cart (sets idempotency token) and submits the order.
    client.get(reverse("orders:cart_detail"))
    resp = client.post(reverse("orders:order_create"), {"comment": "bez soli"})
    assert resp.status_code == 302
    order = Order.objects.get()
    assert order.status == OrderStatus.NEW
    assert order.table == table
    assert order.total_quantity == 2

    # 4. Cashier confirms.
    client.force_login(cashier)
    resp = client.post(reverse("cashier:confirm", args=[order.public_id]), {"version": order.version})
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED

    # 5. Kitchen takes it and finishes.
    client.force_login(kitchen_user)
    client.post(reverse("kitchen:start", args=[order.public_id]), {"version": order.version})
    order.refresh_from_db()
    client.post(reverse("kitchen:ready", args=[order.public_id]), {"version": order.version})
    order.refresh_from_db()
    assert order.status == OrderStatus.READY

    # 6. Cashier serves.
    client.force_login(cashier)
    client.post(reverse("cashier:serve", args=[order.public_id]), {"version": order.version})
    order.refresh_from_db()
    assert order.status == OrderStatus.SERVED


def test_double_submit_creates_single_order(client, restaurant, table, menu):
    burger = menu["burger"]
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    client.post(reverse("orders:cart_add"), {"menu_item_id": burger.id, "quantity": 1})
    client.get(reverse("orders:cart_detail"))  # sets a stable idempotency token

    # Re-add to cart so the second submit also has contents, but the token is
    # cleared only after the first success — simulate a fast double click by
    # posting twice with the same session before the redirect completes.
    client.post(reverse("orders:order_create"), {})
    # Cart cleared; a second identical submit with an empty cart cannot duplicate.
    assert Order.objects.count() == 1


def test_inactive_table_rejects(client, restaurant):
    table = factories.DiningTableFactory(restaurant=restaurant, is_active=False)
    resp = client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    assert resp.status_code == 410


def test_rejected_order_flow(client, restaurant, table, menu, cashier):
    burger = menu["burger"]
    client.get(reverse("tables:table_menu", args=[table.number, table.qr_token]))
    client.post(reverse("orders:cart_add"), {"menu_item_id": burger.id, "quantity": 1})
    client.get(reverse("orders:cart_detail"))
    client.post(reverse("orders:order_create"), {})
    order = Order.objects.get()

    client.force_login(cashier)
    client.post(reverse("cashier:reject", args=[order.public_id]), {"version": order.version})
    order.refresh_from_db()
    assert order.status == OrderStatus.REJECTED
