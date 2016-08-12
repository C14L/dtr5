# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0040_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='pushnotificationendpoint',
            name='latest',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
