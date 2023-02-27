# Generated by Django 4.0.7 on 2023-02-22 15:26

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clinicalcode', '0074_alter_concept_citation_requirements_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenericEntity',
            fields=[
                ('serial_id', models.IntegerField()),
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=250)),
                ('author', models.CharField(max_length=1000)),
                ('layout', models.IntegerField(choices=[(1, 'Clinical-Coded Phenotype'), (2, 'Concept'), (3, 'Working Set'), (4, 'NLP Phenotype'), (5, 'Genomic Phenotype')])),
                ('status', models.IntegerField(choices=[(1, 'Draft'), (2, 'Final')], default=1)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('collections', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('definition', models.TextField(blank=True, null=True)),
                ('implementation', models.TextField(blank=True, null=True)),
                ('validation', models.TextField(blank=True, null=True)),
                ('publications', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=500), blank=True, null=True, size=None)),
                ('citation_requirements', models.TextField(blank=True, null=True)),
                ('template_data', models.JSONField(blank=True, null=True)),
                ('internal_comments', models.TextField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('is_deleted', models.BooleanField(default=False, null=True)),
                ('deleted', models.DateTimeField(blank=True, null=True)),
                ('owner_access', models.IntegerField(choices=[(1, 'No Access'), (2, 'View'), (3, 'Edit')], default=3)),
                ('group_access', models.IntegerField(choices=[(1, 'No Access'), (2, 'View'), (3, 'Edit')], default=1)),
                ('world_access', models.IntegerField(choices=[(1, 'No Access'), (2, 'View'), (3, 'Edit')], default=1)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_created', to=settings.AUTH_USER_MODEL)),
                ('deleted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_deleted', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.group')),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_owned', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.AlterField(
            model_name='historicalphenotypeworkingset',
            name='type',
            field=models.IntegerField(blank=True, choices=[(0, 'Disease or syndrome'), (1, 'Biomarker'), (2, 'Drug'), (3, 'Lifestyle risk factor'), (4, 'Musculoskeletal'), (5, 'Surgical procedure')], default=0, null=True),
        ),
        migrations.AlterField(
            model_name='phenotypeworkingset',
            name='type',
            field=models.IntegerField(blank=True, choices=[(0, 'Disease or syndrome'), (1, 'Biomarker'), (2, 'Drug'), (3, 'Lifestyle risk factor'), (4, 'Musculoskeletal'), (5, 'Surgical procedure')], default=0, null=True),
        ),
        migrations.AlterField(
            model_name='tag',
            name='collection_brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tags_collection_brand', to='clinicalcode.brand'),
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now_add=True)),
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=250, unique=True)),
                ('layout', models.IntegerField(choices=[(1, 'Clinical-Coded Phenotype'), (2, 'Concept'), (3, 'Working Set'), (4, 'NLP Phenotype'), (5, 'Genomic Phenotype')])),
                ('description', models.TextField(blank=True, null=True)),
                ('definition', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='template_created', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='template_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='HistoricalTemplate',
            fields=[
                ('created', models.DateTimeField(blank=True, editable=False)),
                ('modified', models.DateTimeField(blank=True, editable=False)),
                ('id', models.IntegerField(blank=True, db_index=True)),
                ('name', models.CharField(db_index=True, max_length=250)),
                ('layout', models.IntegerField(choices=[(1, 'Clinical-Coded Phenotype'), (2, 'Concept'), (3, 'Working Set'), (4, 'NLP Phenotype'), (5, 'Genomic Phenotype')])),
                ('description', models.TextField(blank=True, null=True)),
                ('definition', models.TextField(blank=True, null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('created_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical template',
                'verbose_name_plural': 'historical templates',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalPublishedGenericEntity',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('entity_history_id', models.IntegerField()),
                ('code_count', models.IntegerField(null=True)),
                ('created', models.DateTimeField(blank=True, editable=False)),
                ('modified', models.DateTimeField(blank=True, editable=False, null=True)),
                ('approval_status', models.IntegerField(default=0)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('created_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('entity', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='clinicalcode.genericentity')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('moderator', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical published generic entity',
                'verbose_name_plural': 'historical published generic entitys',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalGenericEntity',
            fields=[
                ('serial_id', models.IntegerField()),
                ('id', models.CharField(db_index=True, max_length=50)),
                ('name', models.CharField(max_length=250)),
                ('author', models.CharField(max_length=1000)),
                ('layout', models.IntegerField(choices=[(1, 'Clinical-Coded Phenotype'), (2, 'Concept'), (3, 'Working Set'), (4, 'NLP Phenotype'), (5, 'Genomic Phenotype')])),
                ('status', models.IntegerField(choices=[(1, 'Draft'), (2, 'Final')], default=1)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('collections', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('definition', models.TextField(blank=True, null=True)),
                ('implementation', models.TextField(blank=True, null=True)),
                ('validation', models.TextField(blank=True, null=True)),
                ('publications', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=500), blank=True, null=True, size=None)),
                ('citation_requirements', models.TextField(blank=True, null=True)),
                ('template_data', models.JSONField(blank=True, null=True)),
                ('internal_comments', models.TextField(blank=True, null=True)),
                ('created', models.DateTimeField(blank=True, editable=False)),
                ('updated', models.DateTimeField(blank=True, null=True)),
                ('is_deleted', models.BooleanField(default=False, null=True)),
                ('deleted', models.DateTimeField(blank=True, null=True)),
                ('owner_access', models.IntegerField(choices=[(1, 'No Access'), (2, 'View'), (3, 'Edit')], default=3)),
                ('group_access', models.IntegerField(choices=[(1, 'No Access'), (2, 'View'), (3, 'Edit')], default=1)),
                ('world_access', models.IntegerField(choices=[(1, 'No Access'), (2, 'View'), (3, 'Edit')], default=1)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('created_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('deleted_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='auth.group')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='clinicalcode.template')),
                ('updated_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical generic entity',
                'verbose_name_plural': 'historical generic entitys',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name='genericentity',
            name='template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_template', to='clinicalcode.template'),
        ),
        migrations.AddField(
            model_name='genericentity',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entity_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='PublishedGenericEntity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity_history_id', models.IntegerField()),
                ('code_count', models.IntegerField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now_add=True, null=True)),
                ('approval_status', models.IntegerField(default=0)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='published_entity_created_by', to=settings.AUTH_USER_MODEL)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clinicalcode.genericentity')),
                ('moderator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='published_entity_modified_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('entity', 'entity_history_id')},
            },
        ),
    ]