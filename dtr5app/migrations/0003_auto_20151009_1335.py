# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0002_profile_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='updated',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
