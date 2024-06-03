from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0112_dmd_codes'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- i.e. delete previous ontology tag reference(s) post-review
            do $bd$
            begin
                if exists(select 1 from information_schema.columns where table_name='clinicalcode_ontologytag' and column_name='atlas_id') then
                    drop table if exists clinicalcode_ontologytagedge;
                    drop table if exists clinicalcode_ontologytag cascade;
                    delete from django_migrations where app = 'ontologytag';
                end if;
            end; $bd$ language plpgsql;
            """
        ),
    ]
