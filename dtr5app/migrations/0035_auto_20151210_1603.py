# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def change_none_to_one(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Profile = apps.get_model("dtr5app", "Profile")
    for profile in Profile.objects.all():
        # they were unused, so its save to change them to new default
        profile.education = 1
        profile.fitness = 1
        profile.relstatus = 1
        profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0034_auto_20151210_1406'),
    ]

    operations = [
        # Before starting schema migration, fix data to new default value,
        # from None to 1.
        migrations.RunPython(change_none_to_one),

        migrations.AlterField(
            model_name='profile',
            name='education',
            field=models.PositiveSmallIntegerField(default=1, choices=[(1, 'yes'), (2, 'no'), (4, 'other'), (8, 'trade school'), (16, 'high school'), (32, 'university'), (64, 'masters degree'), (128, 'PhD, MD, etc.'), (256, 'self-taught')]),
        ),
        migrations.AlterField(
            model_name='profile',
            name='fitness',
            field=models.PositiveSmallIntegerField(default=1, choices=[(1, "don't know"), (2, 'not really'), (4, 'somewhat'), (8, 'yes'), (16, 'very'), (32, 'a lot')]),
        ),
        migrations.AlterField(
            model_name='profile',
            name='relstatus',
            field=models.PositiveSmallIntegerField(default=1, choices=[(1, "don't know"), (2, 'single'), (4, 'seeing someone'), (8, 'in a relationship'), (16, 'in an open relationship'), (32, 'married')]),
        ),
    ]
