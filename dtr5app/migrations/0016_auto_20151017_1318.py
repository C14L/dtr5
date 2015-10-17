# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0015_profile_pics_str'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='picture',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='picture',
            name='user',
        ),
        migrations.DeleteModel(
            name='Picture',
        ),
    ]
