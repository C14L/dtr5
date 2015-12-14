# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0035_auto_20151210_1603'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='new_likes_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='new_matches_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='new_views_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='upvote_notif_now',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='upvote_notif_weekly',
            field=models.BooleanField(default=True),
        ),
    ]
