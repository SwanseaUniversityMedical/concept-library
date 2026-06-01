from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0136_lang_ontology_en'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            --[!] Create ts agg if not available
            do $$ begin
                create aggregate tsvector_agg(tsvector) (
                    stype    = pg_catalog.tsvector,
                    sfunc    = pg_catalog.tsvector_concat,
                    initcond = ''
                );
            exception
                when duplicate_function then null;
            end $$;


            --[!] Drop legacy trigger(s) if exist
            drop trigger if exists  ot_search_vec_tr on public.clinicalcode_ontologytag;
            drop trigger if exists  ge_search_vec_tr on public.clinicalcode_genericentity;
            drop trigger if exists hge_search_vec_tr on public.clinicalcode_historicalgenericentity;

            drop function if exists  ge_gin_tgram_trigger();
            drop function if exists hge_gin_tgram_trigger();


            --[!] Create utility methods
            create or replace function get_ontological_ancestors(node_ids bigint[])
                returns table(
                    node_id  bigint,
                    path     bigint[]
                )
            language plpgsql as $fn$
            begin
                return query
                with
                    recursive ancestors(child_id, parent_id, depth, path) as (
                      select
                          first.child_id,
                          first.parent_id,
                          1 as depth,
                          array[first.child_id] as path
                        from public.clinicalcode_ontologytagedge as first
                       where first.child_id = any(node_ids)
                       union all
                      select
                          first.child_id,
                          first.parent_id,
                          second.depth + 1 as depth,
                          second.path || first.child_id as path
                        from public.clinicalcode_ontologytagedge as first,
                             ancestors as second
                       where first.child_id = second.parent_id
                         and first.child_id <> all(second.path)
                    )
                select
                    p.child_id as node_id,
                    p.path as path
                  from ancestors as p;
            end
            $fn$;

            create or replace function get_ontological_categories(node_ids bigint[], from_root bigint)
                returns table(
                    id         bigint,
                    categories jsonb
                )
            language plpgsql as $fn$
            begin
                return query
                with
                    paths as (
                      select
                          ont.id,
                          ancestors.path[array_length(ancestors.path, 1) - 1] as cat_id
                        from public.clinicalcode_ontologytag as ont,
                             get_ontological_ancestors(node_ids) as ancestors
                       where ancestors.node_id = from_root
                         and array_length(ancestors.path, 1) > 1
                    )
                select
                    p.id,
                    jsonb_agg(distinct jsonb_build_object(
                      'name', n.name,
                      'ref', n.reference_id
                    )) as categories
                  from paths as p
                  join public.clinicalcode_ontologytag as n
                    on n.id = p.cat_id
                 group by p.id;
            end
            $fn$;


            --[!] Create, update & manage OntologyTag trigger
            create or replace function ot_gin_tgram_trigger()
                returns trigger
                language plpgsql
            as $bd$
            declare
                v_synVec tsvector := null::tsvector;
                v_relVec tsvector := null::tsvector;
            begin
                if (new.properties is not null and jsonb_typeof(new.properties->'synonyms') = 'array') then
                    v_synVec := jsonb_to_tsvector('public.ontology_en', new.properties->'synonyms', '["string"]');
                end if;

                if (new.properties is not null and jsonb_typeof(new.properties->'xrefs') = 'array') then
                    with rels as (
                      select jsonb_agg(regexp_replace(ref, '(\w+)(\.\w+)?:(\w+)', '\1\3', 'g')) as vec
                        from jsonb_array_elements_text(new.properties->'xrefs') as ref
                    )
                    select jsonb_to_tsvector('public.ontology_en', vec, '["string"]')
                      into v_relVec
                      from rels;
                end if;

                new.synonyms_vector := case
                  when v_synVec is not null and length(v_synVec) > 0 then (
                    setweight(to_tsvector('public.ontology_en', new.name), 'A') ||
                    setweight(v_synVec, 'A')
                  )
                  else setweight(to_tsvector('public.ontology_en', new.name), 'A')
                end;

                new.relation_vector := case
                  when v_relVec is not null and length(v_relVec) > 0 then (
                    setweight(to_tsvector('public.ontology_en', replace(lower(new.reference_id), ':', '')), 'A') ||
                    setweight(v_relVec, 'A')
                  )
                  else setweight(to_tsvector('public.ontology_en', replace(lower(new.reference_id), ':', '')), 'A')
                end;

                new.search_vector :=
                    setweight(to_tsvector('public.ontology_en', new.name), 'A') ||
                    setweight(to_tsvector('public.ontology_en', replace(lower(new.reference_id), ':', '')), 'A') ||
                    setweight(coalesce(v_synVec, to_tsvector('')), 'B') ||
                    setweight(coalesce(v_relVec, to_tsvector('')), 'C');

                return new;
            end;
            $bd$;

            create or replace trigger ot_search_vec_tr
            before insert or update
                on public.clinicalcode_ontologytag
            for each row
                execute function ot_gin_tgram_trigger();


            --[!] Create, update & manage GenericEntity and HistoricalGenericEntity triggers
            create or replace function ent_gin_tgram_trigger()
                returns trigger
                language plpgsql AS $$
            declare
                v_ontVec tsvector := null::tsvector;
                v_idxVec tsvector := null::tsvector;
            begin
                --? Attempt to resolve an aggregated search vector from ontological terms associated with this object 
                if (new.template_data is not null and jsonb_typeof(new.template_data->'ontology') = 'array') then
                    select tsvector_agg(coalesce(tag.search_vector, to_tsvector('')))
                      into v_ontVec
                      from jsonb_array_elements_text(new.template_data->'ontology') t(x)
                      join public.clinicalcode_ontologytag as tag
                        on tag.id = cast(x as bigint)
                     where x not like '%[^0-9]%';
                end if;

                --? Attempt to resolve an aggregated search vector from any indexable text field(s) associated with this entity's template
                if (new.template_id is not null and new.template_version is not null) then
                    with
                        tmpl as (
                          select
                              id,
                              history_id,
                              definition->'text_indexable' as indexable,
                              rank() over (
                                partition by id
                                order by history_date desc
                              ) as rn
                            from public.clinicalcode_historicaltemplate
                           where id = new.template_id
                             and template_version = new.template_version
                             and history_type != '-'
                             and definition is not null
                             and definition ? 'text_indexable'
                             and jsonb_typeof(definition->'text_indexable') = 'array'
                        ),
                        indexable as (
                          select array_agg(distinct key)
                            from tmpl as hxt,
                                 jsonb_array_elements_text(hxt.indexable) as t(key)
                           where hxt.rn = 1
                        ),
                        vecs as (
                          select jsonb_agg(distinct value::text) as terms
                            from jsonb_each(new.template_data::jsonb) t(key, value)
                           where key = any((table indexable)::text[])
                             and case jsonb_typeof(value)
                                   when 'string' then true
                                   when 'number' then true
                                   else false
                                 end
                             and length(trim(coalesce(value::text, ''))) > 0
                        )
                    select jsonb_to_tsvector('public.ontology_en', terms, '["string"]')
                      into v_idxVec
                      from vecs;
                end if;

                --> Create aggregated search vector across fields & set appropriate weights
                new.search_vector := 
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.id, '')), 'A') ||
                    setweight(to_tsvector('public.ontology_en', coalesce(new.name, '')), 'A') ||
                    setweight(coalesce(v_ontVec, to_tsvector('')), 'B') ||
                    setweight(coalesce(v_idxVec, to_tsvector('')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(new.author, '')), 'C') ||
                    setweight(to_tsvector('public.ontology_en', coalesce(new.definition, '')), 'D');

                return new;
            end;
            $$;

            create or replace trigger ge_search_vec_tr
            before insert or update
                on public.clinicalcode_genericentity
            for each row
                 execute function ent_gin_tgram_trigger();

            create or replace trigger hge_search_vec_tr
            before insert or update
                on public.clinicalcode_historicalgenericentity
            for each row
                 execute function ent_gin_tgram_trigger();

            """,
            reverse_sql="""
            -- drop trigger(s)
            drop trigger if exists  ot_search_vec_tr on public.clinicalcode_ontologytag;
            drop trigger if exists  ge_search_vec_tr on public.clinicalcode_genericentity;
            drop trigger if exists hge_search_vec_tr on public.clinicalcode_historicalgenericentity;

            -- drop utils
            drop function if exists get_ontological_ancestors(node_ids bigint[]);
            drop function if exists get_ontological_categories(node_ids bigint[], from_root bigint);

            -- drop trigger fn(s)
            drop function if exists  ot_gin_tgram_trigger();
            drop function if exists ent_gin_tgram_trigger();
            """
        ),
    ]
