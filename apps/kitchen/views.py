"""Kitchen display board and preparation actions."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required
from apps.orders import selectors, services
from apps.orders.models import Order
from apps.orders.services import InvalidStatusTransition, OrderConflictError
from apps.restaurants.models import Restaurant


@role_required("is_kitchen")
def board(request):
    restaurant = Restaurant.get_default()
    queue = selectors.kitchen_queue(restaurant.id) if restaurant else {}
    template = "kitchen/_board_columns.html" if request.headers.get("HX-Request") else "kitchen/board.html"
    return render(request, template, {"queue": queue, "restaurant": restaurant})


def _version(request) -> int | None:
    raw = request.POST.get("version")
    return int(raw) if raw and raw.isdigit() else None


def _action(request, public_id, fn, success: str):
    order = get_object_or_404(Order, public_id=public_id)
    try:
        fn(order, user=request.user, expected_version=_version(request))
        messages.success(request, success)
    except (OrderConflictError, InvalidStatusTransition) as exc:
        messages.error(request, str(exc))
    return redirect("kitchen:board")


@role_required("is_kitchen")
@require_POST
def start(request, public_id):
    return _action(request, public_id, services.start_order_preparation, "Príprava začatá.")


@role_required("is_kitchen")
@require_POST
def ready(request, public_id):
    return _action(request, public_id, services.mark_order_ready, "Objednávka pripravená.")


@role_required("is_kitchen")
@require_POST
def back_to_preparation(request, public_id):
    return _action(request, public_id, services.return_to_preparation, "Vrátené do prípravy.")
