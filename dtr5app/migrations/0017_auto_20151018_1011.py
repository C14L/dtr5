# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0016_auto_20151017_1318'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='block_recv_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='block_sent_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='like_recv_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='like_sent_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='matches_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='nope_recv_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='nope_sent_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='views_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
