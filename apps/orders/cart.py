"""Session-backed shopping cart with server-side validation.

The cart is stored in the Django session. Prices are *not* trusted from the
client; every total is recomputed from the live ``MenuItem`` / ``ModifierOption``
records, and availability is re-checked before an order is created.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from apps.menu.models import MenuItem, ModifierGroup, ModifierOption
from apps.menu.services import check_modifier_selection

CART_SESSION_KEY = "cart"


@dataclass
class CartLineModifier:
    option_id: int | None
    menu_item_id: int | None
    group_name: str
    option_name: str
    price_delta: Decimal
    quantity: int = 1


@dataclass
class CartLine:
    line_id: str
    menu_item_id: int
    menu_item_public_id: str
    name: str
    base_price: Decimal
    quantity: int
    comment: str
    modifiers: list[CartLineModifier]

    @property
    def unit_price(self) -> Decimal:
        mods = sum((m.price_delta * m.quantity for m in self.modifiers), Decimal("0.00"))
        return (self.base_price + mods).quantize(Decimal("0.01"))

    @property
    def line_total(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))


class CartError(Exception):
    """User-facing cart validation error."""


class Cart:
    def __init__(self, session):
        self.session = session
        self._raw: dict = session.get(CART_SESSION_KEY, {})

    # Persistence -------------------------------------------------------
    def _save(self) -> None:
        self.session[CART_SESSION_KEY] = self._raw
        self.session.modified = True

    def clear(self) -> None:
        self._raw = {}
        self._save()

    # Mutations ---------------------------------------------------------
    def add(
        self,
        *,
        menu_item_id: int,
        quantity: int,
        comment: str,
        option_ids: list[int],
        menu_item_modifiers: list[dict] | None = None,
    ) -> str:
        if quantity < 1:
            raise CartError("Množstvo musí byť aspoň 1.")
        try:
            item = MenuItem.objects.get(id=menu_item_id)
        except MenuItem.DoesNotExist as exc:
            raise CartError("Položka neexistuje.") from exc
        if not item.can_be_ordered:
            raise CartError(f"Položka „{item.name}“ nie je momentálne dostupná.")

        menu_item_modifiers = menu_item_modifiers or []
        self._validate_modifier_rules(item, option_ids, menu_item_modifiers)

        line_id = uuid.uuid4().hex
        self._raw[line_id] = {
            "menu_item_id": item.id,
            "quantity": int(quantity),
            "comment": comment.strip(),
            "option_ids": [int(o) for o in option_ids],
            "menu_item_modifiers": [
                {"group_id": int(m["group_id"]), "menu_item_id": int(m["menu_item_id"])}
                for m in menu_item_modifiers
            ],
        }
        self._save()
        return line_id

    def update_quantity(self, line_id: str, quantity: int) -> None:
        if line_id not in self._raw:
            raise CartError("Položka v košíku neexistuje.")
        if quantity < 1:
            raise CartError("Množstvo musí byť aspoň 1.")
        self._raw[line_id]["quantity"] = int(quantity)
        self._save()

    def remove(self, line_id: str) -> None:
        if self._raw.pop(line_id, None) is not None:
            self._save()

    def get_raw(self, line_id: str) -> dict | None:
        """Raw stored data for one line (used to pre-fill the edit form)."""
        return self._raw.get(line_id)

    # Validation --------------------------------------------------------
    @staticmethod
    def _validate_modifier_rules(
        item: MenuItem, option_ids: list[int], menu_item_modifiers: list[dict] | None = None
    ) -> None:
        """Enforce required groups and min/max selections on the server."""
        error = check_modifier_selection(item, option_ids, menu_item_modifiers)
        if error:
            raise CartError(error)

    # Reading -----------------------------------------------------------
    def lines(self) -> list[CartLine]:
        result: list[CartLine] = []
        item_ids = [data["menu_item_id"] for data in self._raw.values()]
        items = {i.id: i for i in MenuItem.objects.filter(id__in=item_ids)}
        all_option_ids = {oid for d in self._raw.values() for oid in d["option_ids"]}
        options = {
            o.id: o
            for o in ModifierOption.objects.filter(id__in=all_option_ids).select_related("group")
        }
        menu_modifier_item_ids = {
            raw["menu_item_id"]
            for data in self._raw.values()
            for raw in data.get("menu_item_modifiers", [])
        }
        menu_modifier_items = {
            i.id: i
            for i in MenuItem.objects.filter(id__in=menu_modifier_item_ids).select_related("category")
        }
        menu_modifier_group_ids = {
            raw["group_id"]
            for data in self._raw.values()
            for raw in data.get("menu_item_modifiers", [])
        }
        menu_modifier_groups = {
            g.id: g for g in ModifierGroup.objects.filter(id__in=menu_modifier_group_ids)
        }
        for line_id, data in self._raw.items():
            item = items.get(data["menu_item_id"])
            if item is None:
                continue
            mods = []
            for oid in data["option_ids"]:
                opt = options.get(oid)
                if opt is None:
                    continue
                mods.append(
                    CartLineModifier(
                        option_id=opt.id,
                        menu_item_id=None,
                        group_name=opt.group.name,
                        option_name=opt.name,
                        price_delta=opt.price_delta,
                    )
                )
            for raw in data.get("menu_item_modifiers", []):
                option_item = menu_modifier_items.get(raw["menu_item_id"])
                if option_item is None:
                    continue
                group = menu_modifier_groups.get(raw["group_id"])
                mods.append(
                    CartLineModifier(
                        option_id=None,
                        menu_item_id=option_item.id,
                        group_name=group.name if group else option_item.category.name,
                        option_name=option_item.name,
                        price_delta=option_item.price,
                    )
                )
            result.append(
                CartLine(
                    line_id=line_id,
                    menu_item_id=item.id,
                    menu_item_public_id=str(item.public_id),
                    name=item.name,
                    base_price=item.price,
                    quantity=data["quantity"],
                    comment=data["comment"],
                    modifiers=mods,
                )
            )
        return result

    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self.lines()), Decimal("0.00"))

    @property
    def count(self) -> int:
        return sum(d["quantity"] for d in self._raw.values())

    def is_empty(self) -> bool:
        return not self._raw

    def validate_for_checkout(self) -> list[str]:
        """Return a list of unavailable item names blocking checkout."""
        blocked = []
        for line in self.lines():
            item = MenuItem.objects.filter(id=line.menu_item_id).first()
            if item is None or not item.can_be_ordered:
                blocked.append(line.name)
        return blocked

    def as_order_payload(self) -> list[dict]:
        """Raw cart data used by ``create_order``."""
        return [
            {
                "menu_item_id": d["menu_item_id"],
                "quantity": d["quantity"],
                "comment": d["comment"],
                "option_ids": d["option_ids"],
                "menu_item_modifiers": d.get("menu_item_modifiers", []),
            }
            for d in self._raw.values()
        ]
