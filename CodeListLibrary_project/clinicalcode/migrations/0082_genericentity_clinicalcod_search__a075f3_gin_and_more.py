# Generated by Django 4.0.7 on 2023-03-06 17:10

import django.contrib.postgres.indexes
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0081_search_vector_triggers'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='genericentity',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='clinicalcod_search__a075f3_gin'),
        ),
        migrations.AddIndex(
            model_name='genericentity',
            index=django.contrib.postgres.indexes.GinIndex(fields=['name'], name='ge_name_ln_gin_idx', opclasses=['gin_trgm_ops']),
        ),
        migrations.AddIndex(
            model_name='genericentity',
            index=django.contrib.postgres.indexes.GinIndex(fields=['definition'], name='ge_definition_ln_gin_idx', opclasses=['gin_trgm_ops']),
        ),
        migrations.AddIndex(
            model_name='genericentity',
            index=django.contrib.postgres.indexes.GinIndex(fields=['author'], name='ge_author_ln_gin_idx', opclasses=['gin_trgm_ops']),
        ),
    ]
