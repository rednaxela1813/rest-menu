"""Guest cart and order endpoints (HTML + HTMX fragments)."""
from __future__ import annotations

import logging
import uuid

from django.contrib import messages
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.restaurants.models import Restaurant
from apps.tables.models import DiningTable

from .cart import Cart, CartError
from .models import Order
from .services import OrderValidationError, create_order
from .states import OrderSource

logger = logging.getLogger("orders")
security_logger = logging.getLogger("security")


def _get_table(request) -> DiningTable | None:
    table_id = request.session.get("table_id")
    if not table_id:
        return None
    return DiningTable.objects.filter(id=table_id, is_active=True).first()


def cart_detail(request):
    cart = Cart(request.session)
    # One idempotency token per cart; reused until an order succeeds, so a
    # double submit of the same cart cannot create two orders.
    if not request.session.get("cart_idem"):
        request.session["cart_idem"] = uuid.uuid4().hex
    return render(
        request,
        "orders/cart.html",
        {
            "cart": cart,
            "lines": cart.lines(),
            "table": _get_table(request),
            "idempotency_key": request.session["cart_idem"],
        },
    )


@require_POST
def cart_add(request):
    cart = Cart(request.session)
    is_htmx = request.headers.get("HX-Request") == "true"
    try:
        menu_item_id = int(request.POST["menu_item_id"])
        quantity = int(request.POST.get("quantity", 1))
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Neplatné údaje.")
    # Option ids arrive either under "options" (legacy/tests) or per-group fields
    # named "opt-<group_id>" (so each radio group is independent).
    option_ids = [int(o) for o in request.POST.getlist("options") if o.isdigit()]
    for key, values in request.POST.lists():
        if key.startswith("opt-"):
            option_ids += [int(v) for v in values if v.isdigit()]
    comment = request.POST.get("comment", "")
    # Derive the item's public_id (for the "try again" link) from the DB rather
    # than trusting a hidden form field.
    from apps.menu.models import MenuItem

    public_id = (
        MenuItem.objects.filter(id=menu_item_id)
        .values_list("public_id", flat=True)
        .first()
        or ""
    )

    # When editing an existing cart line we replace it: add the new version,
    # then drop the old one (only after a successful add, so a validation error
    # never loses the original line).
    edit_line = request.POST.get("edit_line", "")

    try:
        cart.add(
            menu_item_id=menu_item_id,
            quantity=quantity,
            comment=comment,
            option_ids=option_ids,
        )
    except CartError as exc:
        if is_htmx:
            # Re-render the inline panel with the error; "try again" reloads the form.
            return render(
                request,
                "orders/_cart_error.html",
                {"error": str(exc), "public_id": public_id},
                status=200,
            )
        messages.error(request, str(exc))
        url = reverse("menu:item_detail", args=[public_id])
        if edit_line:
            url = f"{url}?edit={edit_line}"
        return redirect(url)

    if edit_line:
        cart.remove(edit_line)
        messages.success(request, "Položka bola upravená.")
        return redirect("orders:cart_detail")

    if is_htmx:
        # Confirmation panel + out-of-band update of the cart badge; toast event.
        resp = render(request, "orders/_cart_added.html", {"cart": cart})
        resp["HX-Trigger"] = "itemAdded"
        return resp
    messages.success(request, "Pridané do košíka.")
    return redirect("menu:guest_menu")


@require_http_methods(["POST"])
def cart_update(request, line_id: str):
    cart = Cart(request.session)
    try:
        cart.update_quantity(line_id, int(request.POST.get("quantity", 1)))
    except (CartError, ValueError) as exc:
        messages.error(request, str(exc))
    return redirect("orders:cart_detail")


@require_http_methods(["POST"])
def cart_remove(request, line_id: str):
    Cart(request.session).remove(line_id)
    return redirect("orders:cart_detail")


def _rate_limited(request) -> bool:
    from django.conf import settings

    ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"order_rate:{ip}"
    count = cache.get(key, 0)
    if count >= settings.GUEST_ORDER_RATE_LIMIT:
        security_logger.warning("Order rate limit hit for IP %s", ip)
        return True
    cache.set(key, count + 1, timeout=60)
    return False


@require_POST
def order_create(request):
    cart = Cart(request.session)
    if cart.is_empty():
        messages.error(request, "Košík je prázdny.")
        return redirect("orders:cart_detail")

    if _rate_limited(request):
        messages.error(request, "Príliš veľa objednávok. Skúste o chvíľu.")
        return redirect("orders:cart_detail")

    blocked = cart.validate_for_checkout()
    if blocked:
        messages.error(
            request,
            "Tieto položky už nie sú dostupné, odstráňte ich z košíka: " + ", ".join(blocked),
        )
        return redirect("orders:cart_detail")

    table = _get_table(request)
    restaurant = Restaurant.get_default()
    if restaurant is None:
        raise Http404("Prevádzka nie je nakonfigurovaná.")

    # Idempotency key: the per-cart token set at render time (falls back to a
    # fresh uuid). Reusing it means a rapid double submit returns one order.
    idempotency_key = request.session.get("cart_idem") or uuid.uuid4().hex
    source = OrderSource.QR if table else OrderSource.TABLET

    try:
        order = create_order(
            restaurant=restaurant,
            table=table,
            source=source,
            items=cart.as_order_payload(),
            customer_comment=request.POST.get("comment", ""),
            idempotency_key=idempotency_key,
        )
    except OrderValidationError as exc:
        messages.error(request, str(exc))
        return redirect("orders:cart_detail")

    cart.clear()
    request.session.pop("cart_idem", None)  # next cart gets a fresh token
    request.session["last_order"] = str(order.public_id)
    messages.success(request, f"Objednávka {order.order_number} bola odoslaná.")
    # Return to the menu; the live status chip in the header tracks the order.
    return redirect("menu:guest_menu")


def order_status(request, public_id):
    order = get_object_or_404(
        Order.objects.select_related("table").prefetch_related("items__modifiers"),
        public_id=public_id,
    )
    template = "orders/_status_fragment.html" if request.headers.get("HX-Request") else "orders/order_status.html"
    return render(request, template, {"order": order})


def order_chip(request, public_id):
    """Compact live status chip shown in the menu header (polled / WS-refreshed).

    Returns an empty body once the order has been closed for longer than the
    venue's reset window — the client then removes the chip without a reload.
    """
    from .selectors import status_chip_visible

    order = get_object_or_404(
        Order.objects.select_related("restaurant"), public_id=public_id
    )
    reset_minutes = order.restaurant.order_status_reset_minutes
    if not status_chip_visible(order, reset_minutes):
        if request.session.get("last_order") == str(order.public_id):
            request.session.pop("last_order", None)
        return HttpResponse("")  # empty -> app.js removes the chip element
    return render(request, "orders/_order_chip.html", {"order": order})
