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
        .select_related("menu_item_source_category")
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
                .select_related("modifier_group", "modifier_group__menu_item_source_category")
                .prefetch_related(
                    Prefetch("modifier_group__options", queryset=active_options()),
                    Prefetch("modifier_group__children", queryset=active_children),
                )
                .order_by("sort_order"),
            ),
        )
        .get(public_id=public_id)
    )


def attach_menu_item_modifier_options(
    item: MenuItem, selected_menu_modifier_keys: set[str] | None = None
) -> None:
    """Attach live menu items to modifier groups that source options from a category."""
    selected_menu_modifier_keys = selected_menu_modifier_keys or set()
    groups = []
    for link in item.item_modifier_groups.all():
        group = link.modifier_group
        groups.append(group)
        groups.extend(group.children.all())

    category_ids = {
        group.menu_item_source_category_id
        for group in groups
        if group.menu_item_source_category_id
    }
    if not category_ids:
        return

    items_by_category: dict[int, list[MenuItem]] = {}
    for option_item in (
        MenuItem.objects.filter(
            restaurant_id=item.restaurant_id,
            category_id__in=category_ids,
            is_active=True,
            is_available=True,
        )
        .exclude(id=item.id)
        .order_by("category__sort_order", "sort_order", "name_sk")
    ):
        items_by_category.setdefault(option_item.category_id, []).append(option_item)

    for group in groups:
        category_id = group.menu_item_source_category_id
        menu_options = list(items_by_category.get(category_id, [])) if category_id else []
        group.has_selected_menu_item_option = False
        for option_item in menu_options:
            option_item.is_selected_menu_modifier = (
                f"{group.id}:{option_item.id}" in selected_menu_modifier_keys
            )
            if option_item.is_selected_menu_modifier:
                group.has_selected_menu_item_option = True
        group.menu_item_options = menu_options
