# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0027_auto_20151129_1329'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='f_exclude_sr_li',
            new_name='_f_exclude_sr_li',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='f_ignore_sr_li',
            new_name='_f_ignore_sr_li',
        ),
    ]
