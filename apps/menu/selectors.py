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
    """Fetch a single item with its modifier groups and active options."""
    from .models import ModifierOption

    return (
        MenuItem.objects.select_related("category")
        .prefetch_related(
            "allergens",
            Prefetch(
                "item_modifier_groups",
                queryset=MenuItemModifierGroup.objects.select_related("modifier_group")
                .prefetch_related(
                    Prefetch(
                        "modifier_group__options",
                        queryset=ModifierOption.objects.filter(is_active=True).order_by(
                            "sort_order"
                        ),
                    )
                )
                .order_by("sort_order"),
            ),
        )
        .get(public_id=public_id)
    )
