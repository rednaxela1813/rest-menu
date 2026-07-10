"""Menu domain services shared across apps (e.g. modifier validation)."""
from __future__ import annotations

from .models import MenuItem, MenuItemModifierGroup, ModifierGroup, ModifierOption


def check_modifier_selection(
    item: MenuItem,
    option_ids: list[int],
    menu_item_modifiers: list[dict] | None = None,
) -> str | None:
    """Validate chosen modifier options against an item's groups.

    Returns a Slovak error message, or ``None`` if the selection is valid.
    Callers wrap the message in their own exception type (``CartError`` /
    ``OrderValidationError``) so messages stay in one place.

    Supports nested groups: a top-level *container* group (with ``children``)
    has each child validated by the child's own min/max/required rules, plus an
    optional aggregate cap from the container itself (``max_selections`` 0 means
    no aggregate limit). Leaf groups validate as before.
    """
    links = list(
        MenuItemModifierGroup.objects.filter(menu_item=item)
        .select_related("modifier_group")
        .prefetch_related("modifier_group__children")
    )
    menu_item_modifiers = menu_item_modifiers or []
    options = list(
        ModifierOption.objects.filter(id__in=option_ids, is_active=True).select_related("group")
    )

    valid_ids = {opt.id for opt in options}
    if set(option_ids) - valid_ids:
        return "Vybrali ste neplatný alebo nedostupný modifikátor."

    count_by_group: dict[int, int] = {}
    for opt in options:
        count_by_group[opt.group_id] = count_by_group.get(opt.group_id, 0) + 1

    # Allowed = each linked top-level group plus its child subgroups.
    allowed: set[int] = set()
    allowed_groups: dict[int, ModifierGroup] = {}
    for link in links:
        group = link.modifier_group
        allowed.add(group.id)
        allowed_groups[group.id] = group
        for child in group.children.all():
            allowed.add(child.id)
            allowed_groups[child.id] = child
    for opt in options:
        if opt.group_id not in allowed:
            return "Modifikátor nepatrí k tejto položke."
        if allowed_groups[opt.group_id].menu_item_source_category_id:
            return "Modifikátor nepatrí k tejto položke."

    menu_option_item_ids = []
    for raw in menu_item_modifiers:
        try:
            group_id = int(raw["group_id"])
            menu_item_id = int(raw["menu_item_id"])
        except (KeyError, TypeError, ValueError):
            return "Vybrali ste neplatný alebo nedostupný modifikátor."
        group = allowed_groups.get(group_id)
        if group is None or not group.menu_item_source_category_id:
            return "Modifikátor nepatrí k tejto položke."
        menu_option_item_ids.append(menu_item_id)
        raw["group_id"] = group_id
        raw["menu_item_id"] = menu_item_id

    menu_option_items = {
        option_item.id: option_item
        for option_item in MenuItem.objects.filter(
            id__in=menu_option_item_ids,
            restaurant_id=item.restaurant_id,
            is_active=True,
            is_available=True,
        )
    }
    if set(menu_option_item_ids) - set(menu_option_items):
        return "Vybrali ste neplatný alebo nedostupný modifikátor."

    for raw in menu_item_modifiers:
        group = allowed_groups[raw["group_id"]]
        option_item = menu_option_items[raw["menu_item_id"]]
        if option_item.category_id != group.menu_item_source_category_id:
            return "Modifikátor nepatrí k tejto položke."
        count_by_group[group.id] = count_by_group.get(group.id, 0) + 1

    for link in links:
        group = link.modifier_group
        children = list(group.children.all())
        if children:
            total = 0
            for child in children:
                count = count_by_group.get(child.id, 0)
                total += count
                error = _check_counts(child.name, count, child.min_selections,
                                      child.max_selections, child.is_required)
                if error:
                    return error
            # Optional aggregate cap on the container (overridable per item).
            error = _check_counts(group.name, total, link.effective_min,
                                  link.effective_max, link.effective_required)
            if error:
                return error
        else:
            count = count_by_group.get(group.id, 0)
            error = _check_counts(group.name, count, link.effective_min,
                                  link.effective_max, link.effective_required)
            if error:
                return error
    return None


def _check_counts(name: str, count: int, min_sel: int, max_sel: int, required: bool) -> str | None:
    if required and count < max(1, min_sel):
        return f"Skupina „{name}“ je povinná."
    if count < min_sel:
        return f"V skupine „{name}“ vyberte aspoň {min_sel}."
    if max_sel and count > max_sel:
        return f"V skupine „{name}“ vyberte najviac {max_sel}."
    return None
