# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0020_report_resolved'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='lookingfor',
            field=models.CommaSeparatedIntegerField(default='', max_length=250, blank=True),
        ),
    ]
