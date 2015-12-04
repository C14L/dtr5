# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dtr5app', '0030_auto_20151203_2226'),
    ]

    operations = [
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('hidden', models.BooleanField(default=False)),
                ('host', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, related_name='was_visited')),
                ('visitor', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, related_name='visited')),
            ],
        ),
        migrations.AddField(
            model_name='profile',
            name='f_hide_no_pic',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(serialize=False, related_name='profile', to=settings.AUTH_USER_MODEL, primary_key=True, editable=False),
        ),
    ]
