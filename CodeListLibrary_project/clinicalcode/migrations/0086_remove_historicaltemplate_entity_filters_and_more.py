# Generated by Django 4.0.7 on 2023-03-09 09:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0085_remove_historicaltemplate_entity_order_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicaltemplate',
            name='entity_filters',
        ),
        migrations.RemoveField(
            model_name='historicaltemplate',
            name='entity_statistics',
        ),
        migrations.RemoveField(
            model_name='template',
            name='entity_filters',
        ),
        migrations.RemoveField(
            model_name='template',
            name='entity_statistics',
        ),
    ]
