# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0005_auto_20151010_1115'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscribed',
            name='is_favorite',
            field=models.BooleanField(default=False),
        ),
    ]
