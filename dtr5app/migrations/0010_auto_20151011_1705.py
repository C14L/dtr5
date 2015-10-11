# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0009_picture_src'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='f_distance',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='f_has_verified_email',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='f_maxage',
            field=models.PositiveSmallIntegerField(default=100),
        ),
        migrations.AddField(
            model_name='profile',
            name='f_minage',
            field=models.PositiveSmallIntegerField(default=18),
        ),
        migrations.AddField(
            model_name='profile',
            name='f_over_18',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='f_sex',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='gold_creddits',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='x_has_verified_email',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='x_match_search_options',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='x_min_account_age_days',
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AddField(
            model_name='profile',
            name='x_min_comment_karma',
            field=models.PositiveIntegerField(default=50),
        ),
        migrations.AddField(
            model_name='profile',
            name='x_min_link_karma',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='x_only_no_over_18',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterUniqueTogether(
            name='picture',
            unique_together=set([('user', 'url')]),
        ),
    ]
