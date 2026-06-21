# Mäso pripravujeme vždy "well done" — výber prepečenia už neponúkame.

from django.db import migrations

DONENESS_NAME = "Prepečenie"


def remove_doneness(apps, schema_editor):
    ModifierGroup = apps.get_model("menu", "ModifierGroup")
    MenuItemModifierGroup = apps.get_model("menu", "MenuItemModifierGroup")

    groups = ModifierGroup.objects.filter(name_sk=DONENESS_NAME)
    # Odpojiť skupinu od položiek (toto ju skryje z menu). Väzba nie je
    # referencovaná objednávkami, takže ju možno bezpečne zmazať.
    MenuItemModifierGroup.objects.filter(modifier_group__in=groups).delete()
    # Skupinu ani možnosti nemažeme (OrderItemModifier na ne odkazuje cez
    # PROTECT — zachovávame históriu objednávok), len ich deaktivujeme.
    groups.update(is_active=False)
    for group in groups:
        group.options.update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0002_modifiergroup_collapsed_by_default"),
    ]

    operations = [
        migrations.RunPython(remove_doneness, migrations.RunPython.noop),
    ]
