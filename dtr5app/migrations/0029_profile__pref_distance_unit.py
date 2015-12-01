# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0028_auto_20151129_1934'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='_pref_distance_unit',
            field=models.CharField(default=None, null=True, max_length=2),
        ),
    ]
