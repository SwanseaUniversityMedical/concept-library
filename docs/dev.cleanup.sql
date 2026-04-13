-- vacuum (analyze, verbose);

-- do $$declare r record;
-- begin
--   for r in (
--     select table_name
--       from information_schema.tables
--      where table_name ~ '^(django_|auth_|easyaudit_|clinicalcode_).*$'
--   )
--     loop
--       execute format('reindex table %s.%s;', quote_ident('public'), quote_ident(r.table_name));
--     end loop;
-- end$$;

-- vacuum (full, analyze, verbose);

select
    table_name as name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as total_size,
    pg_size_pretty(pg_relation_size(quote_ident(table_name))) as table_size,
    pg_size_pretty(pg_indexes_size(quote_ident(table_name))) as index_size
  from information_schema.tables
 where table_schema = 'public'
 order by pg_total_relation_size(quote_ident(table_name)) desc;

-- truncate table public.django_session;

-- truncate
--    table public.django_admin_log
--  restart identity;

-- truncate
--    table public.easyaudit_crudevent
--  restart identity;

-- truncate
--    table public.easyaudit_loginevent
--  restart identity;

-- truncate
--    table public.easyaudit_requestevent
--  restart identity;

-- truncate
--    table public.django_celery_beat_periodictask
--  restart identity;

-- truncate
--    table public.django_celery_results_taskresult
--  restart identity;

-- alter sequence public.django_admin_log_id_seq restart with 1;

-- alter sequence public.easyaudit_crudevent_id_seq restart with 1;

-- alter sequence public.easyaudit_loginevent_id_seq restart with 1;

-- alter sequence public.easyaudit_requestevent_id_seq restart with 1;

-- alter sequence public.django_celery_beat_periodictask_id_seq restart with 1;

-- alter sequence public.django_celery_results_taskresult_id_seq restart with 1;

-- begin;
--   create temporary table tmp_code(
--     code text
--   );

--   with
--     ont as (
--       select cast(t0.properties::json->'code' as varchar) as code
--         from public.clinicalcode_ontologytag as t0
--       where json_typeof(t0.properties::json->'code') = 'string'
--       union all
--       select t0.code::varchar
--         from public.clinicalcode_code as t0
--     ),
--     unq as (
--       select code::varchar
--         from ont
--       group by code
--     )
--   insert into tmp_code(code) (
--     select t0.code
--       from public.clinicalcode_snomed_codes as t0
--       left join unq as t1
--         on t0.code = t1.code
--     where t1.code is null
--   );
--   delete
--     from public.clinicalcode_snomed_codes as t0
--   using tmp_code as t1
--   where t0.code = t1.code;
-- commit;

-- begin;
--   create temporary table tmp_code(
--     code text
--   );

--   with
--     unq as (
--       select code
--         from public.clinicalcode_code
--       group by code
--     )
--   insert into tmp_code(code) (
--     select t0.term_id as code
--       from public.clinicalcode_read_cd_cv3_terms_scd as t0
--       left join unq as t1
--         on t0.term_id = t1.code
--     where t1.code is null
--   );
--   delete
--     from public.clinicalcode_read_cd_cv3_terms_scd as t0
--   using tmp_code as t1
--   where t0.term_id = t1.code;
-- commit;

-- with
--   used as (
--     select t1.value::text::bigint
--       from public.clinicalcode_genericentity as t0,
--            json_array_elements(t0.template_data::json->'ontology') as t1
--      where json_typeof(t0.template_data::json->'ontology') = 'array'
--        and json_array_length(t0.template_data::json->'ontology') > 0
--      union all
--     select t1.value::text::bigint
--       from public.clinicalcode_historicalgenericentity as t0,
--            json_array_elements(t0.template_data::json->'ontology') as t1
--      where json_typeof(t0.template_data::json->'ontology') = 'array'
--        and json_array_length(t0.template_data::json->'ontology') > 0
--   ),
--   unq_used as (
--     select value
--       from used
--     group by value
--   )
-- delete
--   from public.clinicalcode_ontologytag as t0
--  where t0.id not in (table unq_used)
--    and t0.id > 100;


-- select t0.*
--   from public.clinicalcode_ontologytag as t0
--  where t0.id in (table unq_used)
  -- join public.clinicalcode_ontologytag as t1
  --   on t0.template_data::json->'ontology' @> t1.id,
