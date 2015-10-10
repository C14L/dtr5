# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0003_auto_20151009_1335'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sr',
            options={'verbose_name': 'Subreddit', 'ordering': ['name'], 'verbose_name_plural': 'Subreddits'},
        ),
        migrations.AlterField(
            model_name='sr',
            name='url',
            field=models.CharField(default='', max_length=50, unique=True),
        ),
        migrations.AlterIndexTogether(
            name='profile',
            index_together=set([('lat', 'lng')]),
        ),
    ]
