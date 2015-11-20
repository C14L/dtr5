# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0019_auto_20151120_2119'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='resolved',
            field=models.DateTimeField(default=None, blank=True, null=True),
        ),
    ]
