"""Cashier kanban board and order actions."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required
from apps.orders import selectors, services
from apps.orders.models import Order
from apps.orders.services import InvalidStatusTransition, OrderConflictError
from apps.restaurants.models import Restaurant


@role_required("is_cashier")
def board(request):
    restaurant = Restaurant.get_default()
    columns = selectors.cashier_board(restaurant.id) if restaurant else {}
    template = "cashier/_board_columns.html" if request.headers.get("HX-Request") else "cashier/board.html"
    return render(request, template, {"columns": columns, "restaurant": restaurant})


@role_required("is_cashier")
def order_detail(request, public_id):
    order = get_object_or_404(
        Order.objects.select_related("table").prefetch_related(
            "items__modifiers", "status_history__changed_by"
        ),
        public_id=public_id,
    )
    return render(request, "cashier/order_detail.html", {"order": order})


def _version(request) -> int | None:
    raw = request.POST.get("version")
    return int(raw) if raw and raw.isdigit() else None


def _action(request, public_id, fn, *, success: str, comment: str = ""):
    order = get_object_or_404(Order, public_id=public_id)
    try:
        if comment:
            fn(order, user=request.user, comment=request.POST.get("comment", ""), expected_version=_version(request))
        else:
            fn(order, user=request.user, expected_version=_version(request))
        messages.success(request, success)
    except OrderConflictError as exc:
        messages.error(request, str(exc))
    except InvalidStatusTransition as exc:
        messages.error(request, str(exc))
    return redirect("cashier:order_detail", public_id=public_id)


@role_required("is_cashier")
@require_POST
def confirm(request, public_id):
    return _action(request, public_id, services.confirm_order, success="Objednávka potvrdená.")


@role_required("is_cashier")
@require_POST
def reject(request, public_id):
    return _action(
        request, public_id, services.reject_order, success="Objednávka zamietnutá.", comment="x"
    )


@role_required("is_cashier")
@require_POST
def cancel(request, public_id):
    return _action(
        request, public_id, services.cancel_order, success="Objednávka zrušená.", comment="x"
    )


@role_required("is_cashier")
@require_POST
def serve(request, public_id):
    return _action(request, public_id, services.mark_order_served, success="Objednávka vydaná.")
