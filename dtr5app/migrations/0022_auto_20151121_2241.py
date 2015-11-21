# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0021_auto_20151121_1150'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='lookingfor',
            new_name='_lookingfor',
        ),
    ]
