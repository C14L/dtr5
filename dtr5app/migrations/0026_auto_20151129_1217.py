# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0025_auto_20151129_1208'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='exclude_sr_li',
            new_name='f_exclude_sr_li',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='ignore_sr_li',
            new_name='f_ignore_sr_li',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='ignore_sr_max',
            new_name='f_ignore_sr_max',
        ),
    ]
