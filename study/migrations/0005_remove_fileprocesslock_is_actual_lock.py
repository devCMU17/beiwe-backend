# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-14 20:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('study', '0004_fileprocesslock_is_actual_lock'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fileprocesslock',
            name='is_actual_lock',
        ),
    ]
