# Generated by Django 4.0.7 on 2023-03-04 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0075_genericentity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genericentity',
            name='entity_id',
            field=models.IntegerField(editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='historicalgenericentity',
            name='entity_id',
            field=models.IntegerField(editable=False, null=True),
        ),
    ]
