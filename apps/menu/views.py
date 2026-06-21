"""Guest-facing menu views."""
from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.restaurants.models import Restaurant
from apps.tables.models import DiningTable

from . import selectors
from .models import MenuCategory, MenuItem


def _get_table(request) -> DiningTable | None:
    table_id = request.session.get("table_id")
    if not table_id:
        return None
    return DiningTable.objects.filter(id=table_id, is_active=True).first()


def guest_menu(request):
    restaurant = Restaurant.get_default()
    if restaurant is None:
        raise Http404("Prevádzka nie je nakonfigurovaná.")
    table = _get_table(request)
    categories = selectors.active_categories(restaurant.id)
    items = selectors.visible_items(restaurant.id)
    items_by_category: dict[int, list] = {}
    for item in items:
        items_by_category.setdefault(item.category_id, []).append(item)
    # Build ordered (category, items) sections so the template stays logic-free.
    sections = [
        (category, items_by_category.get(category.id, []))
        for category in categories
        if items_by_category.get(category.id)
    ]
    from apps.orders.cart import Cart
    from apps.orders.models import Order
    from apps.orders.selectors import status_chip_visible

    # Live status chip for the guest's most recent order (kept in the session).
    # It disappears and resets `order_status_reset_minutes` after the order closes.
    active_order = None
    last_order_id = request.session.get("last_order")
    if last_order_id:
        active_order = Order.objects.filter(public_id=last_order_id).first()
        if not status_chip_visible(active_order, restaurant.order_status_reset_minutes):
            request.session.pop("last_order", None)
            active_order = None

    context = {
        "restaurant": restaurant,
        "table": table,
        "sections": sections,
        "featured": selectors.featured_items(restaurant.id),
        "cart_count": Cart(request.session).count,
        "active_order": active_order,
    }
    return render(request, "menu/guest_menu.html", context)


def category_detail(request, slug: str):
    restaurant = Restaurant.get_default()
    category = get_object_or_404(MenuCategory, restaurant=restaurant, slug=slug, is_active=True)
    items = selectors.visible_items(restaurant.id).filter(category=category)
    return render(
        request,
        "menu/category_detail.html",
        {"restaurant": restaurant, "category": category, "items": items, "table": _get_table(request)},
    )


def item_detail(request, public_id):
    """Full-page item configuration — used as a no-JS fallback and to EDIT a
    cart line (``?edit=<line_id>`` pre-fills the current selections)."""
    try:
        item = selectors.item_with_modifiers(public_id)
    except MenuItem.DoesNotExist as exc:
        raise Http404("Položka neexistuje.") from exc

    selected_ids: set[int] = set()
    edit_quantity, edit_comment, edit_line = 1, "", ""
    edit = request.GET.get("edit")
    if edit:
        from apps.orders.cart import Cart

        raw = Cart(request.session).get_raw(edit)
        if raw and raw["menu_item_id"] == item.id:
            selected_ids = set(raw["option_ids"])
            edit_quantity = raw["quantity"]
            edit_comment = raw["comment"]
            edit_line = edit

    return render(
        request,
        "menu/item_detail.html",
        {
            "item": item,
            "table": _get_table(request),
            "selected_ids": selected_ids,
            "edit_quantity": edit_quantity,
            "edit_comment": edit_comment,
            "edit_line": edit_line,
        },
    )


def item_config(request, public_id):
    """Inline modifier panel loaded into the dish card via HTMX (no page change).

    Groups are split into:
      * visible — upsell/required (fries, drinks, doneness) shown immediately;
      * hidden  — optional composition edits (add/remove ingredients) behind a
        collapsible toggle, so the kitchen isn't flooded with changes.
    """
    try:
        item = selectors.item_with_modifiers(public_id)
    except MenuItem.DoesNotExist as exc:
        raise Http404("Položka neexistuje.") from exc

    visible_links, hidden_links = [], []
    for link in item.item_modifier_groups.all():
        if link.modifier_group.collapsed_by_default and not link.effective_required:
            hidden_links.append(link)
        else:
            visible_links.append(link)

    return render(
        request,
        "menu/_item_config.html",
        {"item": item, "visible_links": visible_links, "hidden_links": hidden_links},
    )
