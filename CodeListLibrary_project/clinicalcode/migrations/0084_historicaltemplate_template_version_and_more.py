# Generated by Django 4.0.7 on 2023-03-07 17:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0083_remove_genericentity_entity_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaltemplate',
            name='template_version',
            field=models.IntegerField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='template',
            name='template_version',
            field=models.IntegerField(editable=False, null=True),
        ),
    ]