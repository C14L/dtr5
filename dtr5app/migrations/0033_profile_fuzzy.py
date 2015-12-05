# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0032_auto_20151204_2344'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='fuzzy',
            field=models.IntegerField(default=2),
        ),
    ]
