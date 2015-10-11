# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0008_auto_20151010_2249'),
    ]

    operations = [
        migrations.AddField(
            model_name='picture',
            name='src',
            field=models.CharField(max_length=150, default=''),
        ),
    ]
