# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dtr5app', '0011_profile_about'),
    ]

    operations = [
        migrations.CreateModel(
            name='Flag',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('flag', models.PositiveSmallIntegerField(choices=[(1, 'like'), (2, 'nope'), (3, 'block')])),
                ('created', models.DateTimeField(default=datetime.datetime(2015, 10, 16, 21, 29, 28, 16741, tzinfo=utc))),
                ('receiver', models.ForeignKey(related_name='flags_received', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(related_name='flags_sent', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterModelOptions(
            name='subscribed',
            options={'ordering': ['sr__display_name'], 'verbose_name': 'subreddit subscription', 'verbose_name_plural': 'subreddit subscriptions'},
        ),
    ]
