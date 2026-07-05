"""The seed command builds the fries/sauce groups and the nested drink tree."""
import pytest
from django.core.management import call_command

from apps.menu.models import MenuItem, ModifierGroup

pytestmark = pytest.mark.django_db


def test_seed_builds_modifier_tree():
    call_command("seed_demo")

    # Doneness ("Prepečenie") is intentionally gone.
    assert not ModifierGroup.objects.filter(name_sk="Prepečenie").exists()

    sides = ModifierGroup.objects.get(name_sk="Príloha")
    sauce = ModifierGroup.objects.get(name_sk="Omáčka")
    assert sides.options.count() == 6
    assert sauce.options.count() == 6

    drinks = ModifierGroup.objects.get(name_sk="Nápoj", parent__isnull=True)
    children = {c.name_sk for c in drinks.children.all()}
    assert children == {"Pivo", "Víno", "Nealko"}
    # Container has no own options; each subcategory does.
    assert drinks.options.count() == 0
    assert all(c.options.exists() for c in drinks.children.all())

    # Burgers link only the top-level groups (subcategories ride along the tree).
    burger = MenuItem.objects.get(slug="kovboj")
    linked = {link.modifier_group.name_sk for link in burger.item_modifier_groups.all()}
    assert {"Príloha", "Omáčka", "Nápoj"} <= linked
    assert "Pivo" not in linked


def test_seed_is_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    # Re-running must not duplicate the drink container or its subcategories.
    assert ModifierGroup.objects.filter(name_sk="Nápoj", parent__isnull=True).count() == 1
    assert ModifierGroup.objects.filter(name_sk="Pivo").count() == 1
