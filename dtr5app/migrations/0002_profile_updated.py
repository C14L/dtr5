# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='updated',
            field=models.DateField(default=None, null=True),
        ),
    ]
