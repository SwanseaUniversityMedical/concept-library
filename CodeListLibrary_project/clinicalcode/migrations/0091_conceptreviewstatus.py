# Generated by Django 4.0.7 on 2023-03-20 13:14

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clinicalcode', '0090_icd10_codes_and_titles_and_metadata_icd10_code_ln_gin_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConceptReviewStatus',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('concept_id', models.IntegerField(blank=True, null=True)),
                ('history_id', models.IntegerField(blank=True, null=True)),
                ('review_submitted', models.BooleanField(default=False, null=True)),
                ('included_codes', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('excluded_codes', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('comment', models.TextField(blank=True, null=True)),
                ('last_reviewed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_concepts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
