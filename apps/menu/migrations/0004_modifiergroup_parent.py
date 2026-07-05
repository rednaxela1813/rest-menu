import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0003_remove_doneness_modifier"),
    ]

    operations = [
        migrations.AddField(
            model_name="modifiergroup",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="menu.modifiergroup",
                verbose_name="nadradená skupina",
            ),
        ),
    ]
