# Generated by Django 4.0.10 on 2023-08-02 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0106_component_used_description_component_used_wildcard_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='index_path',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='historicalbrand',
            name='index_path',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]