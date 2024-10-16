# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2021-07-19 19:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0031_auto_20210712_1451'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaltag',
            name='collection_brand',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='clinicalcode.Brand'),
        ),
        migrations.AddField(
            model_name='tag',
            name='collection_brand',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tags_collection_brand',
                to='clinicalcode.Brand'),
        ),
    ]
