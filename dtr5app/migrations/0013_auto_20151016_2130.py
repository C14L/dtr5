# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0012_auto_20151016_2129'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flag',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
