# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0038_pushnotificationendpoint'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pushnotificationendpoint',
            name='endpoint',
        ),
        migrations.RemoveField(
            model_name='pushnotificationendpoint',
            name='keys',
        ),
        migrations.AddField(
            model_name='pushnotificationendpoint',
            name='sub',
            field=models.CharField(unique=True, default='', max_length=2000),
            preserve_default=False,
        ),
    ]
