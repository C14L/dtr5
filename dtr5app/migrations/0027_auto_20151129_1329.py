# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0026_auto_20151129_1217'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='f_ignore_sr_max',
            field=models.PositiveIntegerField(default=100000000),
        ),
    ]
