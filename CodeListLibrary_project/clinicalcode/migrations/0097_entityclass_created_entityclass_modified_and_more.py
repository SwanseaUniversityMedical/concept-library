# Generated by Django 4.0.10 on 2023-04-24 09:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clinicalcode', '0096_alter_genericentity_group_access_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityclass',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name='entityclass',
            name='modified',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name='entityclass',
            name='modified_by',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_class_updater', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='entityclass',
            name='created_by',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_class_creator', to=settings.AUTH_USER_MODEL),
        ),
    ]
