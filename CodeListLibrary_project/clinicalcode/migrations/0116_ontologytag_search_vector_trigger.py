from django.db import migrations
from django.db import connection
from django.contrib.postgres.search import SearchVector

def compute_search_vectors(apps, schema_editor):
    with connection.cursor() as cursor:
        sql = '''
        update public.clinicalcode_ontologytag as trg
           set search_vector =
                setweight(to_tsvector('pg_catalog.english', coalesce(name, '')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(properties::json->>'code'::text, '')), 'B')

        '''
        cursor.execute(sql)

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0115_ontologytag_search_vector_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            create function ot_gin_tgram_trigger() returns trigger
            language plpgsql AS $$
            begin
                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.properties::json->>'code'::text, '')), 'B');
                return new;
            end;
            $$;

            create trigger ot_search_vec_tr
            before insert or update
                on public.clinicalcode_ontologytag
            for each row
                execute function ot_gin_tgram_trigger();

            update public.clinicalcode_ontologytag
               set search_vector = null;
            """,
            reverse_sql="""
            drop trigger if exists ot_search_vec_tr on public.clinicalcode_ontologytag
            """
        ),
        migrations.RunPython(compute_search_vectors, reverse_code=migrations.RunPython.noop),
    ]
