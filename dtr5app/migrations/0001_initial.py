# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('user', models.OneToOneField(primary_key=True, serialize=False, related_name='profile', to=settings.AUTH_USER_MODEL)),
                ('name', models.CharField(max_length=20, default='')),
                ('created', models.DateField(default=None, null=True)),
                ('link_karma', models.IntegerField(default=0)),
                ('comment_karma', models.IntegerField(default=0)),
                ('over_18', models.BooleanField(default=False)),
                ('hide_from_robots', models.BooleanField(default=False)),
                ('has_verified_email', models.BooleanField(default=False)),
                ('lat', models.FloatField(default=None, null=True)),
                ('lng', models.FloatField(default=None, null=True)),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
            },
        ),
        migrations.CreateModel(
            name='Sr',
            fields=[
                ('id', models.CharField(primary_key=True, serialize=False, max_length=10)),
                ('name', models.CharField(max_length=50, editable=False)),
                ('created', models.DateField(default=None, null=True)),
                ('url', models.CharField(max_length=50, default='')),
                ('over18', models.BooleanField(default=False)),
                ('lang', models.CharField(max_length=10, default='')),
                ('title', models.CharField(max_length=100, default='')),
                ('header_title', models.CharField(max_length=100, default='')),
                ('display_name', models.CharField(max_length=100, default='')),
                ('subreddit_type', models.CharField(max_length=50, default='')),
                ('subscribers', models.IntegerField(default=0)),
                ('subscribers_here', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Subreddit',
                'verbose_name_plural': 'Subreddits',
            },
        ),
        migrations.CreateModel(
            name='Subscribed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('user_is_contributor', models.BooleanField(default=False)),
                ('user_is_moderator', models.BooleanField(default=False)),
                ('user_is_subscriber', models.BooleanField(default=True)),
                ('user_is_banned', models.BooleanField(default=False)),
                ('user_is_muted', models.BooleanField(default=False)),
                ('sr', models.ForeignKey(editable=False, related_name='users', to='dtr5app.Sr')),
                ('user', models.ForeignKey(editable=False, related_name='subs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Subreddit subscription',
                'verbose_name_plural': 'Subreddit subscriptions',
            },
        ),
    ]
