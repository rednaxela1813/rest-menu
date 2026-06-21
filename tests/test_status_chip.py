"""Order-status chip visibility + admin-configurable reset window."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.orders import services
from apps.orders.selectors import status_chip_visible
from apps.orders.states import OrderSource
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(restaurant, burger):
    return services.create_order(
        restaurant=restaurant,
        source=OrderSource.QR,
        items=[{"menu_item_id": burger.id, "quantity": 1, "comment": "", "option_ids": []}],
    )


@pytest.fixture
def burger(restaurant):
    category = factories.MenuCategoryFactory(restaurant=restaurant)
    return factories.MenuItemFactory(restaurant=restaurant, category=category)


def test_open_order_chip_always_visible(order):
    assert status_chip_visible(order, reset_minutes=3) is True


def test_closed_order_visible_within_window(order, cashier, kitchen_user):
    services.confirm_order(order, user=cashier)
    services.start_order_preparation(order, user=kitchen_user)
    services.mark_order_ready(order, user=kitchen_user)
    services.mark_order_served(order, user=cashier)
    order.refresh_from_db()
    assert status_chip_visible(order, reset_minutes=3) is True


def test_closed_order_hidden_after_window(order, cashier, kitchen_user):
    services.confirm_order(order, user=cashier)
    services.start_order_preparation(order, user=kitchen_user)
    services.mark_order_ready(order, user=kitchen_user)
    services.mark_order_served(order, user=cashier)
    order.refresh_from_db()
    # Pretend it was served 4 minutes ago.
    order.served_at = timezone.now() - timedelta(minutes=4)
    order.save(update_fields=["served_at"])
    assert status_chip_visible(order, reset_minutes=3) is False


def test_reset_window_is_configurable(restaurant, order, cashier):
    services.cancel_order(order, user=cashier)
    order.refresh_from_db()
    order.cancelled_at = timezone.now() - timedelta(minutes=5)
    order.save(update_fields=["cancelled_at"])
    assert status_chip_visible(order, reset_minutes=3) is False
    assert status_chip_visible(order, reset_minutes=10) is True


def test_chip_endpoint_returns_empty_when_expired(client, restaurant, order, cashier):
    services.cancel_order(order, user=cashier)
    order.refresh_from_db()
    order.cancelled_at = timezone.now() - timedelta(minutes=10)
    order.save(update_fields=["cancelled_at"])
    resp = client.get(reverse("orders:order_chip", args=[order.public_id]))
    assert resp.status_code == 200
    assert resp.content.decode().strip() == ""


def test_chip_endpoint_renders_for_open_order(client, order):
    resp = client.get(reverse("orders:order_chip", args=[order.public_id]))
    assert resp.status_code == 200
    assert "order-chip__dot--new" in resp.content.decode()
