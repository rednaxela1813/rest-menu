"""Read-only query helpers for the menu domain."""
from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from .models import MenuCategory, MenuItem, MenuItemModifierGroup


def active_categories(restaurant_id: int) -> QuerySet[MenuCategory]:
    return MenuCategory.objects.filter(restaurant_id=restaurant_id, is_active=True).order_by(
        "sort_order", "name_sk"
    )


def visible_items(restaurant_id: int) -> QuerySet[MenuItem]:
    """Items shown to guests (active); availability is rendered separately."""
    return (
        MenuItem.objects.filter(restaurant_id=restaurant_id, is_active=True)
        .select_related("category")
        .prefetch_related("allergens")
        .order_by("category__sort_order", "sort_order", "name_sk")
    )


def featured_items(restaurant_id: int) -> QuerySet[MenuItem]:
    return visible_items(restaurant_id).filter(is_featured=True, is_available=True)[:8]


def item_with_modifiers(public_id) -> MenuItem:
    """Fetch a single item with its modifier groups, child subgroups and options.

    Only active groups/options are loaded. Top-level groups may be *containers*
    whose ``children`` (e.g. Pivo/Víno/Nealko under "Nápoj") each carry their own
    options; both levels are prefetched so the template can render nested
    accordions without extra queries.
    """
    from .models import ModifierGroup, ModifierOption

    def active_options():
        return ModifierOption.objects.filter(is_active=True).order_by("sort_order")

    active_children = (
        ModifierGroup.objects.filter(is_active=True)
        .order_by("sort_order")
        .prefetch_related(
            Prefetch("options", queryset=active_options()),
            # Cache the (always-empty, one-level rule) grandchildren so
            # ``is_container`` on a subcategory doesn't trigger a query each.
            "children",
        )
    )

    return (
        MenuItem.objects.select_related("category")
        .prefetch_related(
            "allergens",
            Prefetch(
                "item_modifier_groups",
                queryset=MenuItemModifierGroup.objects.filter(modifier_group__is_active=True)
                .select_related("modifier_group")
                .prefetch_related(
                    Prefetch("modifier_group__options", queryset=active_options()),
                    Prefetch("modifier_group__children", queryset=active_children),
                )
                .order_by("sort_order"),
            ),
        )
        .get(public_id=public_id)
    )
