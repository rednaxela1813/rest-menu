"""factory_boy factories for the test suite."""
from __future__ import annotations

from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from apps.menu.models import (
    MenuCategory,
    MenuItem,
    MenuItemModifierGroup,
    ModifierGroup,
    ModifierOption,
)
from apps.restaurants.models import Restaurant
from apps.tables.models import DiningTable

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@test.local")
    role = "cashier"
    is_staff = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "pass1234")
        if create:
            obj.save()


class RestaurantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Restaurant

    name = "Test Burger"
    slug = factory.Sequence(lambda n: f"test-burger-{n}")
    currency = "EUR"


class DiningTableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiningTable

    restaurant = factory.SubFactory(RestaurantFactory)
    number = factory.Sequence(lambda n: n + 1)


class MenuCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MenuCategory

    restaurant = factory.SubFactory(RestaurantFactory)
    name_sk = factory.Sequence(lambda n: f"Kategória {n}")
    slug = factory.Sequence(lambda n: f"kategoria-{n}")


class MenuItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MenuItem

    restaurant = factory.SubFactory(RestaurantFactory)
    category = factory.SubFactory(
        MenuCategoryFactory, restaurant=factory.SelfAttribute("..restaurant")
    )
    name_sk = factory.Sequence(lambda n: f"Burger {n}")
    slug = factory.Sequence(lambda n: f"burger-{n}")
    price = Decimal("8.00")


class ModifierGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ModifierGroup

    name_sk = factory.Sequence(lambda n: f"Skupina {n}")
    selection_type = "MULTIPLE"
    min_selections = 0
    max_selections = 3


class ModifierOptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ModifierOption

    group = factory.SubFactory(ModifierGroupFactory)
    name_sk = factory.Sequence(lambda n: f"Možnosť {n}")
    price_delta = Decimal("0.00")


class MenuItemModifierGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MenuItemModifierGroup

    menu_item = factory.SubFactory(MenuItemFactory)
    modifier_group = factory.SubFactory(ModifierGroupFactory)
