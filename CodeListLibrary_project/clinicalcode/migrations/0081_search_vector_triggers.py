from django.db import migrations
from django.contrib.postgres.search import SearchVector

def compute_search_vectors(apps, schema_editor):
    GenericEntity = apps.get_model('clinicalcode', 'GenericEntity')
    GenericEntity.objects.update(search_vector=SearchVector('name', 'definition', 'author'))

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0080_genericentity_search_vector_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER ge_search_vec_tr
            BEFORE INSERT OR UPDATE OF name, definition, author, search_vector
            ON clinicalcode_genericentity
            FOR EACH ROW EXECUTE PROCEDURE
            tsvector_update_trigger(search_vector, 'pg_catalog.english', name, definition, author);
            UPDATE clinicalcode_genericentity SET search_vector = NULL;
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS ge_search_vec_tr ON clinicalcode_genericentity
            """
        ),
        migrations.RunPython(compute_search_vectors, reverse_code=migrations.RunPython.noop)
    ]
