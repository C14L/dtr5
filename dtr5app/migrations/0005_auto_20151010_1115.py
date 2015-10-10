# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0004_auto_20151009_1545'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sr',
            options={'verbose_name': 'Subreddit', 'ordering': ['display_name'], 'verbose_name_plural': 'Subreddits'},
        ),
        migrations.AlterField(
            model_name='profile',
            name='lat',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='profile',
            name='lng',
            field=models.FloatField(default=0.0),
        ),
    ]
