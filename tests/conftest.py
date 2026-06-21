import pytest

from tests import factories


@pytest.fixture
def restaurant(db):
    return factories.RestaurantFactory()


@pytest.fixture
def table(db, restaurant):
    return factories.DiningTableFactory(restaurant=restaurant)


@pytest.fixture
def category(db, restaurant):
    return factories.MenuCategoryFactory(restaurant=restaurant)


@pytest.fixture
def burger(db, restaurant, category):
    from decimal import Decimal

    return factories.MenuItemFactory(
        restaurant=restaurant, category=category, price=Decimal("8.00")
    )


@pytest.fixture
def admin_user(db):
    return factories.UserFactory(role="admin", is_superuser=True, is_staff=True)


@pytest.fixture
def cashier(db):
    return factories.UserFactory(role="cashier")


@pytest.fixture
def kitchen_user(db):
    return factories.UserFactory(role="kitchen")
