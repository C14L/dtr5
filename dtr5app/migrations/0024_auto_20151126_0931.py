# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0023_auto_20151121_2252'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='pics_str',
            new_name='_pics',
        ),
        migrations.AddField(
            model_name='profile',
            name='accessed',
            field=models.DateTimeField(null=True, default=None),
        ),
    ]
