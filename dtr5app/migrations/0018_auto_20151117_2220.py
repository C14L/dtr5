# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtr5app', '0017_auto_20151018_1011'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='education',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(2, 'high school'), (4, 'trade school'), (6, 'university'), (8, 'masters degree'), (10, 'PhD, MD, etc.'), (12, 'yes'), (14, 'no')], default=None),
        ),
        migrations.AddField(
            model_name='profile',
            name='fitness',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, 'not really'), (2, 'somewhat'), (3, 'yes'), (4, 'very'), (5, 'even more')], default=None),
        ),
        migrations.AddField(
            model_name='profile',
            name='height',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='profile',
            name='lookingfor',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, 'someone to chat'), (2, 'hugs and nice words'), (3, 'new friends'), (4, 'sexy time'), (5, 'dating'), (6, 'serious dating'), (7, 'a relationship'), (8, 'marriage'), (9, 'house+car+kids... now!'), (10, 'just another cat'), (11, 'my car keys'), (12, 'world peace'), (13, 'the grand unified theory'), (14, 'this is getting ridiculous'), (15, 'stahp!'), (16, 'just some nice person, really')], default=None),
        ),
        migrations.AddField(
            model_name='profile',
            name='relstatus',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(2, 'single'), (4, 'seeing someone'), (6, 'in a relationship'), (8, 'open relationship'), (10, 'married')], default=None),
        ),
        migrations.AddField(
            model_name='profile',
            name='tagline',
            field=models.CharField(max_length=160, default=''),
        ),
        migrations.AddField(
            model_name='profile',
            name='weight',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
