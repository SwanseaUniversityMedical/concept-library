-- 1. create table(s)
-- Quote: " | Escape: null
create table tmp_mesh_rel (
  id     serial        primary key,
  child  varchar(18)   not null,
  parent varchar(18)   not null
);

-- Quote: " | Escape: null
create table tmp_mesh_desc (
  id     serial        primary key,
  code   varchar(18)   not null,
  name   varchar(512)  not null,
  type   varchar(18)   not null
);


-- 2. Import data...

--[[ ... ]]--


-- 3. Run the following to create
--  -> Coding Mesh ID: 26
--  -> Reference Mesh Id: 3
--
insert into public.clinicalcode_ontologytag (name, type_id, properties, search_vector)
  select
      mesh.name,
      3 as type_id,
      json_build_object(
        'code', mesh.code,
        'coding_system_id', 26,
        'type', mesh.type
      ) as properties,
      setweight(
        (to_tsvector('pg_catalog.english', coalesce(mesh.name, '')) || to_tsvector('pg_catalog.english', coalesce(mesh.code, ''))),
        'A'
      ) as search_vector
    from tmp_mesh_desc as mesh;


-- 4. Build relationships
with
  ontology as (
    select
          id,
          properties::json->>'code'::varchar as code
      from public.clinicalcode_ontologytag
     where type_id = 3
  ),
  relationships as (
    select *
      from public.tmp_mesh_rel
  )
insert into public.clinicalcode_ontologytagedge (child_id, parent_id)
  select
        c.id as child_id,
        p.id as parent_id
    from relationships as r
    join ontology as c
      on r.child = c.code
    join ontology as p
      on r.parent = p.code
 on conflict (child_id, parent_id) do nothing;


-- 5. Drop tmp table(s)
drop table tmp_mesh_rel;
drop table tmp_mesh_desc;
