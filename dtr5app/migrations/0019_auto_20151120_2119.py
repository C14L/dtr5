# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dtr5app', '0018_auto_20151117_2220'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('reason', models.PositiveSmallIntegerField(choices=[(1, 'spam'), (2, 'personal information'), (3, 'inapropriate picture'), (4, 'sexualizing minors'), (5, 'other (write below)')])),
                ('details', models.TextField(default='')),
                ('receiver', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='reports_received')),
                ('sender', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='reports_sent')),
            ],
            options={
                'verbose_name_plural': 'user reports',
                'verbose_name': 'user report',
            },
        ),
        migrations.AlterField(
            model_name='flag',
            name='flag',
            field=models.PositiveSmallIntegerField(choices=[(1, 'like'), (2, 'nope'), (3, 'block'), (4, 'report')]),
        ),
        migrations.AlterIndexTogether(
            name='report',
            index_together=set([('sender', 'receiver'), ('reason', 'receiver')]),
        ),
    ]
