# Generated by Django 4.0.7 on 2023-03-06 17:03

import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0079_install_extensions'),
    ]

    operations = [
        migrations.AddField(
            model_name='genericentity',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AddField(
            model_name='historicalgenericentity',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
    ]