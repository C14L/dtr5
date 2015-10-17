# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0014_auto_20151016_2214'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='pics_str',
            field=models.TextField(default=''),
        ),
    ]
