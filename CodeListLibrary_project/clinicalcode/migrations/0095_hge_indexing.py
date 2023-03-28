from django.db import migrations
from django.contrib.postgres.search import SearchVector

def compute_search_vectors(apps, schema_editor):
    HistoricalGenericEntity = apps.get_model('clinicalcode', 'HistoricalGenericEntity')
    HistoricalGenericEntity.objects.update(search_vector=SearchVector('name', 'definition', 'author'))

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0094_genericentity_ge_impl_ln_gin_idx_and_more'),
    ]

    operations = [
        # Historic search trigger
        migrations.RunSQL(
            sql="""
            CREATE FUNCTION hge_gin_tgram_trigger() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.id,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.author,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.definition,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.implementation,'')), 'D') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.validation,'')), 'D');
                return new;
            end;
            $$;

            CREATE TRIGGER hge_search_vec_tr BEFORE INSERT OR UPDATE
            ON clinicalcode_historicalgenericentity
            FOR EACH ROW EXECUTE FUNCTION hge_gin_tgram_trigger();

            UPDATE clinicalcode_historicalgenericentity SET search_vector = NULL;
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS hge_search_vec_tr ON clinicalcode_historicalgenericentity
            """
        ),
        migrations.RunPython(compute_search_vectors, reverse_code=migrations.RunPython.noop),

        # Trigram indexing
        migrations.RunSQL(
            sql="""CREATE INDEX hge_sv_idx ON "clinicalcode_historicalgenericentity" USING gin (search_vector);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""CREATE INDEX hge_id_ln_gin_idx ON "clinicalcode_historicalgenericentity" USING gin (id gin_trgm_ops);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""CREATE INDEX hge_name_ln_gin_idx ON "clinicalcode_historicalgenericentity" USING gin (name gin_trgm_ops);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""CREATE INDEX hge_definition_ln_gin_idx ON "clinicalcode_historicalgenericentity" USING gin (definition gin_trgm_ops);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""CREATE INDEX hge_author_ln_gin_idx ON "clinicalcode_historicalgenericentity" USING gin (author gin_trgm_ops);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""CREATE INDEX hge_impl_ln_gin_idx ON "clinicalcode_historicalgenericentity" USING gin (implementation gin_trgm_ops);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""CREATE INDEX hge_val_ln_gin_idx ON "clinicalcode_historicalgenericentity" USING gin (validation gin_trgm_ops);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
