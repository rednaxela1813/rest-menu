"""Populate the database with demo data (restaurant, menu, tables, staff)."""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.menu.models import (
    Allergen,
    MenuCategory,
    MenuItem,
    MenuItemModifierGroup,
    ModifierGroup,
    ModifierOption,
)
from apps.restaurants.models import Restaurant
from apps.tables.models import DiningTable

User = get_user_model()


class Command(BaseCommand):
    help = "Vytvorí demo dáta: prevádzku, menu, stoly a používateľov."

    @transaction.atomic
    def handle(self, *args, **options):
        restaurant, _ = Restaurant.objects.get_or_create(
            slug="burger-bar",
            defaults={"name": "Burger Bar", "currency": "EUR", "default_language": "sk"},
        )
        self.stdout.write(self.style.SUCCESS(f"Prevádzka: {restaurant}"))

        self._create_users()
        self._create_tables(restaurant)
        allergens = self._create_allergens()
        groups = self._create_modifier_groups()
        self._create_menu(restaurant, allergens, groups)

        self.stdout.write(self.style.SUCCESS("Demo dáta pripravené."))

    def _create_users(self) -> None:
        accounts = [
            ("admin@burger.local", "admin", True, True),
            ("kasa@burger.local", "cashier", False, True),
            ("kuchyna@burger.local", "kitchen", False, True),
        ]
        for email, role, is_super, is_staff in accounts:
            user, created = User.objects.get_or_create(
                email=email, defaults={"role": role, "is_staff": is_staff, "is_superuser": is_super}
            )
            if created:
                user.set_password("heslo1234")
                user.save()
                self.stdout.write(f"  používateľ {email} / heslo1234 ({role})")

    def _create_tables(self, restaurant: Restaurant) -> None:
        for i in range(1, 9):
            DiningTable.objects.get_or_create(
                restaurant=restaurant, number=i, defaults={"sort_order": i}
            )
        DiningTable.objects.get_or_create(
            restaurant=restaurant, number=100, defaults={"name": "Bar", "sort_order": 100}
        )
        self.stdout.write("  stoly 1–8 + Bar")

    def _create_allergens(self) -> dict[str, Allergen]:
        data = {"1": "Lepok", "3": "Vajcia", "7": "Mlieko", "10": "Horčica"}
        result = {}
        for code, name in data.items():
            allergen, _ = Allergen.objects.get_or_create(code=code, defaults={"name": name})
            result[code] = allergen
        return result

    def _create_modifier_groups(self) -> dict[str, ModifierGroup]:
        groups: dict[str, ModifierGroup] = {}

        # Mäso pripravujeme vždy "well done", preto výber prepečenia neponúkame.

        # Upsell: side dish — VISIBLE by default (marketing).
        sides, _ = ModifierGroup.objects.update_or_create(
            name_sk="Vyberte prílohu",
            defaults={
                "selection_type": "SINGLE",
                "min_selections": 0,
                "max_selections": 1,
                "is_required": False,
                "collapsed_by_default": False,
                "sort_order": 1,
            },
        )
        for name, price, default in [
            ("Bez prílohy", "0.00", True),
            ("Hranolky", "2.50", False),
            ("Sladké zemiaky", "3.00", False),
        ]:
            ModifierOption.objects.get_or_create(
                group=sides, name_sk=name, defaults={"price_delta": Decimal(price), "is_default": default}
            )
        groups["sides"] = sides

        # Upsell: drink — VISIBLE by default (marketing).
        drinks, _ = ModifierGroup.objects.update_or_create(
            name_sk="Vyberte nápoj",
            defaults={
                "selection_type": "SINGLE",
                "min_selections": 0,
                "max_selections": 1,
                "is_required": False,
                "collapsed_by_default": False,
                "sort_order": 2,
            },
        )
        for name, price, default in [
            ("Bez nápoja", "0.00", True),
            ("Kofola 0,5l", "2.10", False),
            ("Minerálka", "1.50", False),
        ]:
            ModifierOption.objects.get_or_create(
                group=drinks, name_sk=name, defaults={"price_delta": Decimal(price), "is_default": default}
            )
        groups["drinks"] = drinks

        # Composition edits — HIDDEN by default (kept off the kitchen's radar).
        extras, _ = ModifierGroup.objects.update_or_create(
            name_sk="Extra ingrediencie",
            defaults={
                "selection_type": "MULTIPLE",
                "min_selections": 0,
                "max_selections": 4,
                "collapsed_by_default": True,
                "sort_order": 10,
            },
        )
        for name, price in [("Extra slanina", "1.50"), ("Extra syr", "1.00"), ("Extra mäso", "3.00")]:
            ModifierOption.objects.get_or_create(
                group=extras, name_sk=name, defaults={"price_delta": Decimal(price)}
            )
        groups["extras"] = extras

        remove, _ = ModifierGroup.objects.update_or_create(
            name_sk="Odobrať ingrediencie",
            defaults={
                "selection_type": "MULTIPLE",
                "min_selections": 0,
                "max_selections": 5,
                "collapsed_by_default": True,
                "sort_order": 11,
            },
        )
        for name in ["Bez cibule", "Bez uhorky", "Bez omáčky"]:
            ModifierOption.objects.get_or_create(group=remove, name_sk=name)
        groups["remove"] = remove

        return groups

    def _create_menu(self, restaurant, allergens, groups) -> None:
        burgers, _ = MenuCategory.objects.get_or_create(
            restaurant=restaurant, slug="burgre", defaults={"name_sk": "Burgre", "sort_order": 1}
        )
        sides, _ = MenuCategory.objects.get_or_create(
            restaurant=restaurant, slug="prilohy", defaults={"name_sk": "Prílohy", "sort_order": 2}
        )
        drinks, _ = MenuCategory.objects.get_or_create(
            restaurant=restaurant, slug="napoje", defaults={"name_sk": "Nápoje", "sort_order": 3}
        )

        # Burgers offer fries + drinks (visible upsell) and hidden composition edits.
        burger_groups = ["sides", "drinks", "extras", "remove"]
        items = [
            (burgers, "Kovboj", "8.90", True, burger_groups, ["1", "7"]),
            (burgers, "Klasik", "7.50", True, burger_groups, ["1", "7"]),
            (sides, "Hranolky", "3.20", False, [], ["1"]),
            (drinks, "Kofola 0,5l", "2.10", False, [], []),
        ]
        for category, name, price, featured, group_keys, allergen_codes in items:
            item, created = MenuItem.objects.get_or_create(
                restaurant=restaurant,
                slug=slugify(name),
                defaults={
                    "category": category,
                    "name_sk": name,
                    "price": Decimal(price),
                    "is_featured": featured,
                    "estimated_preparation_minutes": 12 if category == burgers else 5,
                },
            )
            if created:
                item.allergens.set([allergens[c] for c in allergen_codes if c in allergens])
            # Re-sync modifier links idempotently so re-running the seed updates them.
            for idx, key in enumerate(group_keys):
                MenuItemModifierGroup.objects.update_or_create(
                    menu_item=item,
                    modifier_group=groups[key],
                    defaults={"sort_order": idx},
                )
        self.stdout.write("  menu: 4 položky, 3 kategórie, upsell prílohy+nápoje")
