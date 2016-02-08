# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def subscribed_is_fav_all_true(apps, schema_editor):
    # Set all values: Subscribed.is_favorite = True
    subs = apps.get_model("dtr5app", "Subscribed")
    subs.objects.all().update(is_favorite=True)


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0036_auto_20151214_1111'),
    ]

    operations = [
        migrations.RunPython(subscribed_is_fav_all_true),

        migrations.AddField(
            model_name='profile',
            name='f_is_stable',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='subscribed',
            name='is_favorite',
            field=models.BooleanField(default=True),
        ),
    ]
