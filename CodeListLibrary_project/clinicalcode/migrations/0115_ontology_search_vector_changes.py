from django.db import migrations
from django.db import connection

def compute_live_and_historical_ge_ontology_vecs(apps, schema_editor):
    with connection.cursor() as cursor:
        sql = '''
        --[!] create ts agg if not available
        do $$ begin
            create aggregate tsvector_agg(tsvector) (
                stype    = pg_catalog.tsvector,
                sfunc    = pg_catalog.tsvector_concat,
                initcond = ''
            );
        exception
            when duplicate_function then null;
        end $$;


        --[!] update search vector for OntologyTag;
        update public.clinicalcode_ontologytag as trg
           set search_vector =
                setweight(to_tsvector('pg_catalog.english', coalesce(name, '')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(properties::json->>'code'::text, '')), 'A') ||
                setweight(coalesce(relation_vector, to_tsvector('')), 'B') ||
                setweight(coalesce(synonyms_vector, to_tsvector('')), 'B');


        --[!] update search vector for GenericEntity;
        with
            ge_ontologies as (
                select
                        entity.id,
                        tsvector_agg(coalesce(tag.search_vector, to_tsvector(''))) as search_vector
                  from public.clinicalcode_genericentity as entity
                  join public.clinicalcode_ontologytag as tag
                    on tag.id = any(array(select json_array_elements_text(entity.template_data::json->'ontology'))::int[])
                 group by entity.id
            )
        update public.clinicalcode_genericentity as trg
           set search_vector =
                setweight(to_tsvector('pg_catalog.english', coalesce(src.id,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.name,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.author,'')), 'B') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.definition,'')), 'B') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.implementation,'')), 'D') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.validation,'')), 'D') ||
                coalesce(src.ts_data, to_tsvector(''))
           from (
             select entity.*,
                    t.search_vector as ts_data
               from public.clinicalcode_genericentity as entity
               join ge_ontologies as t
                 on t.id = entity.id
           ) as src
          where src.id = trg.id;


        --[!] update search vector for HistoricalGenericEntity;
        with
            hge_ontologies as (
                select
                        entity.id,
                        entity.history_id,
                        tsvector_agg(coalesce(tag.search_vector, to_tsvector(''))) as search_vector
                  from public.clinicalcode_historicalgenericentity as entity
                  join public.clinicalcode_ontologytag as tag
                    on tag.id = any(array(select json_array_elements_text(entity.template_data::json->'ontology'))::int[])
                 group by entity.id, entity.history_id
            )
        update public.clinicalcode_historicalgenericentity as trg
           set search_vector =
                setweight(to_tsvector('pg_catalog.english', coalesce(src.id,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.name,'')), 'A') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.author,'')), 'B') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.definition,'')), 'B') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.implementation,'')), 'D') ||
                setweight(to_tsvector('pg_catalog.english', coalesce(src.validation,'')), 'D') ||
                coalesce(src.ts_data, to_tsvector(''))
           from (
             select entity.*,
                    t.search_vector as ts_data
               from public.clinicalcode_historicalgenericentity as entity
               join hge_ontologies as t
                 on t.id = entity.id
                and t.history_id = entity.history_id
           ) as src
          where src.id = trg.id
            and src.history_id = trg.history_id;

        '''
        cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0114_ontologytag_ontologytagedge_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            --[!] create ts agg if not available
            do $$ begin
                create aggregate tsvector_agg(tsvector) (
                    stype    = pg_catalog.tsvector,
                    sfunc    = pg_catalog.tsvector_concat,
                    initcond = ''
                );
            exception
                when duplicate_function then null;
            end $$;


            --[!] create partial btree index on OntologyTag properties
            create index if not exists ot_bt_code_idx
                on public.clinicalcode_ontologytag
             using btree ((properties->>'code'));

            create index if not exists ot_bt_code_id_idx
                on public.clinicalcode_ontologytag
             using btree ((properties->>'code_id'));

            create index if not exists ot_bt_code_system_idx
                on public.clinicalcode_ontologytag
             using btree ((properties->>'code'), (properties->>'coding_system_id'));


            --[!] create, update & manage OntologyTag trigger;
            create or replace function ot_gin_tgram_trigger() returns trigger
            language plpgsql AS $bd$
            begin
                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.properties::json->>'code'::text, '')), 'A') ||
                    setweight(coalesce(new.relation_vector, to_tsvector('')), 'B') ||
                    setweight(coalesce(new.synonyms_vector, to_tsvector('')), 'B');

                new.relation_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.properties::json->>'code'::text, '')), 'A') ||
                    setweight(coalesce(new.synonyms_vector, to_tsvector('')), 'B');

                return new;
            end;
            $bd$;

            create trigger ot_search_vec_tr
            before insert or update
                on public.clinicalcode_ontologytag
            for each row
                execute function ot_gin_tgram_trigger();

            update public.clinicalcode_ontologytag
               set search_vector = null;


            --[!] create, update & manage GenericEntity trigger;
            create or replace function ge_gin_tgram_trigger() returns trigger
            language plpgsql AS $$
            declare
                ts_data tsvector;
            begin
                select
                      tsvector_agg(coalesce(tag.search_vector, to_tsvector('')))
                  from (values (array(select json_array_elements_text(new.template_data::json->'ontology'))::int[])) as t(ontology_ids)
                  join public.clinicalcode_ontologytag as tag
                    on tag.id = any(ontology_ids)
                  into ts_data;

                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.id,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.author,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.definition,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.implementation,'')), 'D') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.validation,'')), 'D') ||
                    coalesce(ts_data, to_tsvector(''));
                return new;
            end;
            $$;

            create or replace trigger ge_search_vec_tr
            before insert or update
                on clinicalcode_genericentity
            for each row
                execute function ge_gin_tgram_trigger();

            update clinicalcode_genericentity
               set search_vector = null;


            --[!] create, update & manage HistoricalGenericEntity trigger;
            create or replace function hge_gin_tgram_trigger() returns trigger
            language plpgsql AS $$
            declare
                ts_data tsvector;
            begin
                select
                      tsvector_agg(coalesce(tag.search_vector, to_tsvector('')))
                  from (values (array(select json_array_elements_text(new.template_data::json->'ontology'))::int[])) as t(ontology_ids)
                  join public.clinicalcode_ontologytag as tag
                    on tag.id = any(ontology_ids)
                  into ts_data;

                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.id,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.author,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.definition,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.implementation,'')), 'D') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.validation,'')), 'D') ||
                    coalesce(ts_data, to_tsvector(''));
                return new;
            end;
            $$;

            create or replace trigger hge_search_vec_tr
            before insert or update
                on clinicalcode_historicalgenericentity
            for each row
                execute function hge_gin_tgram_trigger();

            update clinicalcode_historicalgenericentity
               set search_vector = null;

            """,
            reverse_sql="""
            drop trigger if exists ot_search_vec_tr on public.clinicalcode_ontologytag;
            drop trigger if exists ge_search_vec_tr on public.clinicalcode_genericentity;
            drop trigger if exists hge_search_vec_tr on public.clinicalcode_historicalgenericentity;
            """
        ),
        migrations.RunPython(compute_live_and_historical_ge_ontology_vecs, reverse_code=migrations.RunPython.noop),
    ]
