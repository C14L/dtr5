# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dtr5app', '0007_auto_20151010_1842'),
    ]

    operations = [
        migrations.CreateModel(
            name='Picture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('url', models.CharField(max_length=150)),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='pics', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'picture',
                'verbose_name_plural': 'pictures',
            },
        ),
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'user profile', 'verbose_name_plural': 'user profiles'},
        ),
        migrations.AlterModelOptions(
            name='sr',
            options={'verbose_name': 'subreddit', 'verbose_name_plural': 'subreddits', 'ordering': ['display_name']},
        ),
        migrations.AlterModelOptions(
            name='subscribed',
            options={'verbose_name': 'subreddit subscription', 'verbose_name_plural': 'subreddit subscriptions'},
        ),
        migrations.AlterField(
            model_name='profile',
            name='sex',
            field=models.IntegerField(choices=[(0, 'other'), (1, 'woman who likes men'), (2, 'woman who likes women'), (3, 'woman who likes queer'), (4, 'man who likes women'), (5, 'man who likes men'), (6, 'man who likes queer'), (7, 'queer who likes women'), (8, 'queer who likes men'), (9, 'queer who likes queer')], default=0),
        ),
    ]
