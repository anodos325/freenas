# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-05-26 12:58
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0022_remove_smb_doscharset'),
    ]

    operations = [
        migrations.AddField(
            model_name='cifs',
            name='cifs_srv_allow_smb1',
            field=models.BooleanField(default=False,
                help_text=(
                    'Use this option to allow legacy SMB clients to connect to the'
                    'server. Note that SMB1 is being deprecated and it is advised'
                    'to upgrade clients to operating system versions that support'
                    'modern versions of the SMB protocol.'
                ),
                verbose_name='Allow SMB1 clients'
        ),
    ]
