# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0013_auto_20151016_2130'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='flag',
            options={'verbose_name': 'user flag', 'verbose_name_plural': 'user flags'},
        ),
        migrations.AlterUniqueTogether(
            name='flag',
            unique_together=set([('sender', 'receiver', 'flag')]),
        ),
    ]
