# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0033_profile_fuzzy'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='background_pic',
            field=models.CharField(max_length=250, default=''),
        ),
        migrations.AddField(
            model_name='profile',
            name='herefor',
            field=models.PositiveIntegerField(choices=[(1, 'only dating'), (2, 'mostly dating'), (4, 'friends or dating'), (8, 'mostly friends'), (16, 'only friends')], default=4),
        ),
        migrations.AddField(
            model_name='profile',
            name='herefor_exclude',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
