/********************************************************************************
 * ICD-9 & MeSH table(s)                                                        *
 *                                                                              *
 *  ? Create base source-target tables                                          *
 *                                                                              *
 ********************************************************************************/
create table public.temp_icd9_sct_map (
  id     serial        primary key,
  source varchar(7)    not null,       -- Source : ICD-9 Code
  target varchar(18)   not null        -- Target : SNOMED Code
);

create table public.temp_cuid_mesh_map (
  id     serial        primary key,
  cuid   varchar(18)   not null,       -- CUID   : Unique identifier
  source varchar(18)   not null,       -- Source : One of [ MSH | SNOMEDCT ]
  target varchar(18)   not null        -- Target : Source code / term
);

create table public.temp_mesh_sct_map (
  id     serial        primary key,
  source varchar(18)   not null,       -- Source : MeSH Code
  target varchar(18)   not null        -- Target : SNOMED Code
);

create table public.temp_mesh_codes (
  id              serial        primary key,
  code            varchar(10)   not null,
  description     varchar(256)  not null,
  parent          varchar(10)   default null,
  record_type     integer       not null default 0,
  record_category integer       not null default 0,
  record_modifier integer       not null default 0
);


/********************************************************************************
 * Build MeSH table                                                             *
 *                                                                              *
 *  ? Generate MeSH table such that parent reference(s) are collapsed into      *
 *    a single array field                                                      *
 *                                                                              *
 *     -> We're not looking to support its hierarchical nature quite yet,       *
 *        so the intention is to collapse the records into a single field       *
 *                                                                              *
 *     -> This will allow us to iterate on it in the future by destructuring    *
 *        the `parent_codes` field                                              *
 *                                                                              *
 ********************************************************************************/

-- insert into mesh table
with
  codemap as (
      select
            code,
            description,
            array_agg(parent)::text[] as parent_codes,
            record_type,
            record_category,
            record_modifier
        from public.temp_mesh_codes
       group by code, description, record_type, record_category, record_modifier
  )
insert into public.clinicalcode_mesh_codes (
  code, description,
  parent_codes, record_type,
  record_category, record_modifier,
  active, effective_time
)
  select
        code,
		    description,
        array_remove(parent_codes, null) as parent_codes,
        record_type,
        record_category,
        record_modifier,
        true as active,
        current_timestamp as effective_time
    from codemap;


/********************************************************************************
 * Build base MeSH map                                                          *
 *                                                                              *
 *  ? Generate simplified map table                                             *
 *                                                                              *
 ********************************************************************************/
with
  mesh_map as (
    select
          cuid,
          target
      from public.temp_cuid_mesh_map
     where source ilike '%msh%'
  ),
  snomed_map as (
    select
          cuid,
          target
      from public.temp_cuid_mesh_map
     where source ilike '%snomed%'
  )
insert into public.temp_mesh_sct_map (
  source,
  target
)
  select
        t0.target as source,
        t1.target as target
    from mesh_map as t0
    join snomed_map as t1
      on t0.cuid = t1.cuid;


/********************************************************************************
 * Build mapping                                                                *
 *                                                                              *
 *  ? Generate final mapping tables...                                          *
 *     -> icd9map: ICD-9 to SNOMED map                                          *
 *     -> meshmap: MeSH  to SNOMED map                                          *
 *                                                                              *
 ********************************************************************************/
do $tx$
begin
  -- drop table if exists
  if exists(
    select 1
      from information_schema.tables
    where table_schema = 'public'
      and table_name in ('temp_icd9map', 'temp_meshmap')
  ) then
    drop table if exists public.temp_icd9map cascade;
    drop table if exists public.temp_meshmap cascade;
  end if;

  -- create icd9->sct map table
  --
  --   NOTE:
  --     - See `GOMED/.docs` repo for ICD-9 processing
  --     - Created by mapping tables via Bash
  --
  create table public.temp_icd9map (
    id          serial        primary key,
    codes       text[]        default '{}'::text[],
    snomed_code varchar(18)   not null,
    unique (snomed_code)
  );

  -- build final icd-9 map
  with
    codemap as (
        select
            target,
            array_agg(source)::text[] as codes
        from public.temp_icd9_sct_map
       group by target
    )
  insert into public.temp_icd9map (
    codes, snomed_code
  )
    select
          codes,
          target as snomed_code
      from codemap;

  -- create mesh->sct map table
  --
  --   NOTE:
  --     - See `termspp` repo for MeSH processing
  --
  create table public.temp_meshmap (
    id          serial        primary key,
    codes       text[]        default '{}'::text[],
    snomed_code varchar(18)   not null,
    unique (snomed_code)
  );

  -- build final mesh map
  with
    codemap as (
        select
            target,
            array_agg(source)::text[] as codes
        from public.temp_mesh_sct_map
       group by target
    )
  insert into public.temp_meshmap (
    codes, snomed_code
  )
    select
          codes,
          target as snomed_code
      from codemap;
end;
$tx$ language plpgsql;
