from django.db import migrations
from django.db import connection

def compute_search_vectors(apps, schema_editor):
    with connection.cursor() as cursor:
        sql = '''
        with
            ontology_tags as (
                select
                        entity.id,
                        string_agg(format('%s %s', tag.name, coalesce(tag.properties::jsonb->>'code'::text, '')), ' ') AS tags
                  from public.clinicalcode_genericentity as entity
                  join public.clinicalcode_ontologytag as tag
                    on tag.id = any(array(select json_array_elements_text(entity.template_data::json->'ontology'))::int[])
                 group by entity.id
            )

        update public.clinicalcode_genericentity as trg
           set search_vector =
                setweight(to_tsvector('pg_catalog.english', coalesce(src.id,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.name,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.ts_data,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.author,'')), 'B') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.definition,'')), 'B') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.implementation,'')), 'D') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.validation,'')), 'D')
           from (
             select entity.*, t.tags as ts_data
               from public.clinicalcode_genericentity as entity
               join ontology_tags as t
                 on t.id = entity.id
           ) as src
          where src.id = trg.id;
        '''
        cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0116_ontologytag_search_vector_trigger'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION ge_gin_tgram_trigger() RETURNS trigger
            LANGUAGE plpgsql AS $$
            DECLARE
                ts_data TEXT;
            BEGIN

                SELECT
                        string_agg(format('%s %s', tag.name, coalesce(tag.properties::jsonb->>'code'::text, '')), ' ') AS ontology_tags
                  FROM (VALUES (array(select json_array_elements_text(new.template_data::json->'ontology'))::int[])) AS t(ontology_ids)
                  JOIN public.clinicalcode_ontologytag as tag
                    ON tag.id = any(ontology_ids)
                  INTO ts_data;

                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.id,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(ts_data,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.author,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.definition,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.implementation,'')), 'D') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.validation,'')), 'D');
                RETURN new;
            END;
            $$;

            CREATE OR REPLACE TRIGGER ge_search_vec_tr BEFORE INSERT OR UPDATE
            ON clinicalcode_genericentity
            FOR EACH ROW EXECUTE FUNCTION ge_gin_tgram_trigger();

            UPDATE clinicalcode_genericentity SET search_vector = NULL;
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS ge_search_vec_tr ON clinicalcode_genericentity
            """
        ),
        migrations.RunPython(compute_search_vectors, reverse_code=migrations.RunPython.noop),
    ]
