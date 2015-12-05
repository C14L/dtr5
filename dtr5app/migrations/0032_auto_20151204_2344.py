# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0031_auto_20151204_0114'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='visit',
            options={'verbose_name_plural': 'visits', 'ordering': ['-created'], 'verbose_name': 'visit'},
        ),
    ]
