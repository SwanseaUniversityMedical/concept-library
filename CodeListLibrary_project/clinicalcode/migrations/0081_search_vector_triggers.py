from django.db import migrations
from django.contrib.postgres.search import SearchVector

def compute_search_vectors(apps, schema_editor):
    GenericEntity = apps.get_model('clinicalcode', 'GenericEntity')
    GenericEntity.objects.update(search_vector=SearchVector(
        'id',
        'name',
        'definition',
        'author',
        'definition',
        'implementation',
        'validation',
        'publications'
    ))

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0080_genericentity_search_vector_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE FUNCTION ge_gin_tgram_trigger() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.id,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.author,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.definition,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.implementation,'')), 'D') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.validation,'')), 'D') ||
                    setweight(to_tsvector('pg_catalog.english', array_to_string(new.publications,' ')), 'D');
                RETURN new;
            END;
            $$;

            CREATE TRIGGER ge_search_vec_tr BEFORE INSERT OR UPDATE
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
