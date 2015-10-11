# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0006_subscribed_is_favorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='dob',
            field=models.DateField(null=True, default=None),
        ),
        migrations.AddField(
            model_name='profile',
            name='sex',
            field=models.IntegerField(default=0, choices=[(0, 'other'), (1, 'male'), (2, 'female'), (2, 'queer')]),
        ),
    ]
