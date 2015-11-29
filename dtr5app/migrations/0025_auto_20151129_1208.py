# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0024_auto_20151126_0931'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='exclude_sr_li',
            field=models.CharField(max_length=250, default=''),
        ),
        migrations.AddField(
            model_name='profile',
            name='ignore_sr_li',
            field=models.CharField(max_length=250, default=''),
        ),
        migrations.AddField(
            model_name='profile',
            name='ignore_sr_max',
            field=models.PositiveIntegerField(default=10000000),
        ),
        migrations.AlterField(
            model_name='sr',
            name='display_name',
            field=models.CharField(db_index=True, max_length=100, default=''),
        ),
    ]
