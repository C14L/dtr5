# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0022_auto_20151121_2241'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='_lookingfor',
            field=models.CommaSeparatedIntegerField(max_length=50, default='', blank=True),
        ),
    ]
