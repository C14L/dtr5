# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dtr5app', '0037_profile_f_is_stable'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushNotificationEndpoint',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('endpoint', models.CharField(max_length=1000, unique=True)),
                ('keys', models.CharField(max_length=1000)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='endpoints')),
            ],
        ),
    ]
