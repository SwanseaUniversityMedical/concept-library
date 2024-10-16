# Generated by Django 4.0.10 on 2023-07-21 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0105_genericentity_brands_historicalgenericentity_brands'),
    ]

    operations = [
        migrations.AddField(
            model_name='component',
            name='used_description',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='component',
            name='used_wildcard',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='component',
            name='was_wildcard_sensitive',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalcomponent',
            name='used_description',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalcomponent',
            name='used_wildcard',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalcomponent',
            name='was_wildcard_sensitive',
            field=models.BooleanField(default=False),
        ),
    ]
