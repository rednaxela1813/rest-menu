"""Order status finite-state machine: allowed and forbidden transitions."""
import pytest

from apps.orders import services
from apps.orders.states import (
    ALLOWED_TRANSITIONS,
    InvalidStatusTransition,
    OrderSource,
    OrderStatus,
    can_transition,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(restaurant, burger):
    return services.create_order(
        restaurant=restaurant,
        source=OrderSource.QR,
        items=[{"menu_item_id": burger.id, "quantity": 1, "comment": "", "option_ids": []}],
    )


def test_new_to_confirmed_allowed(order, cashier):
    services.confirm_order(order, user=cashier)
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED
    assert order.confirmed_at is not None
    assert order.confirmed_by == cashier


def test_full_happy_path(order, cashier, kitchen_user):
    services.confirm_order(order, user=cashier)
    services.start_order_preparation(order, user=kitchen_user)
    services.mark_order_ready(order, user=kitchen_user)
    services.mark_order_served(order, user=cashier)
    order.refresh_from_db()
    assert order.status == OrderStatus.SERVED
    assert order.served_at is not None


def test_cannot_serve_a_new_order(order, cashier):
    with pytest.raises(InvalidStatusTransition):
        services.mark_order_served(order, user=cashier)


def test_cannot_start_preparation_before_confirm(order, kitchen_user):
    with pytest.raises(InvalidStatusTransition):
        services.start_order_preparation(order, user=kitchen_user)


def test_served_is_terminal(order, cashier, kitchen_user):
    services.confirm_order(order, user=cashier)
    services.start_order_preparation(order, user=kitchen_user)
    services.mark_order_ready(order, user=kitchen_user)
    services.mark_order_served(order, user=cashier)
    with pytest.raises(InvalidStatusTransition):
        services.cancel_order(order, user=cashier)


def test_ready_can_return_to_preparation(order, cashier, kitchen_user):
    services.confirm_order(order, user=cashier)
    services.start_order_preparation(order, user=kitchen_user)
    services.mark_order_ready(order, user=kitchen_user)
    services.return_to_preparation(order, user=kitchen_user)
    order.refresh_from_db()
    assert order.status == OrderStatus.IN_PREPARATION


def test_transition_table_helper():
    assert can_transition(OrderStatus.NEW, OrderStatus.CONFIRMED)
    assert not can_transition(OrderStatus.NEW, OrderStatus.READY)
    assert ALLOWED_TRANSITIONS[OrderStatus.SERVED] == set()


def test_each_transition_records_history(order, cashier):
    services.confirm_order(order, user=cashier)
    history = list(order.status_history.all())
    # creation entry + confirm entry
    assert history[-1].previous_status == OrderStatus.NEW
    assert history[-1].new_status == OrderStatus.CONFIRMED
    assert history[-1].changed_by == cashier
