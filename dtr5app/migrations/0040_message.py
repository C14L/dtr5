# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dtr5app', '0039_auto_20160728_1507'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('msg', models.CharField(max_length=240)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('receiver', models.ForeignKey(on_delete=models.SET_NULL, null=True, to=settings.AUTH_USER_MODEL, related_name='received_messages')),
                ('sender', models.ForeignKey(on_delete=models.SET_NULL, null=True, to=settings.AUTH_USER_MODEL, related_name='sent_messages')),
            ],
            options={
                'verbose_name': 'private message',
                'verbose_name_plural': 'private messages',
                'ordering': ['-id'],
            },
        ),
    ]
