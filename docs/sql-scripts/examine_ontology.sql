/**********************************
 *                                *
 *       Ontology debugging       *
 *                                *
 **********************************/

-------------------------------------------------------------

-- Update matched values for ontology

update public.clinicalcode_ontologytag as trg
   set properties = properties || jsonb_build_object('code_id', src.code_id)
  from (
    select node.id as node_id,
           code.id as code_id
      from public.clinicalcode_ontologytag as node
      join public.clinicalcode_icd10_codes_and_titles_and_metadata as code
        on replace(node.properties->>'code'::text, '.', '') = replace(code.code, '.', '')
     where node.properties is not null
       and node.properties ? 'code'
       and node.type_id = 0
       and code.effective_to is null
  ) src
  where trg.id = src.node_id
    and trg.type_id = 0
    and trg.properties is not null;



-------------------------------------------------------------

-- Test ontology selection

select node.id as node_id,
       code.id as code_id
  from public.clinicalcode_ontologytag as node
  join public.clinicalcode_icd10_codes_and_titles_and_metadata as code
    on replace(node.properties->>'code'::text, '.', '') = replace(code.code, '.', '')
 where node.properties is not null
   and node.properties ? 'code'
   and node.type_id = 0
   and code.effective_to is null;



-------------------------------------------------------------

-- View valid rows

select count(*) as total,
       sum(case when node.properties is not null and node.properties ? 'code_id' then 1 else 0 end) as with_code_id,
       sum(case when node.properties is not null and node.properties ? 'code_id' then 0 else 1 end) as without_code_id
  from public.clinicalcode_ontologytag as node
 where node.type_id = 0;

select *
  from public.clinicalcode_ontologytag as node
 where node.type_id = 0
   and node.properties->>'code_id' is null;


/**********************************
 *                                *
 *       Ontology traversal       *
 *                                *
 **********************************/

-------------------------------------------------------------

-- Attempt to find path of ontology node

with
  recursive descendants(parent_id, child_id, depth, path) as (
    select n0.parent_id,
           n0.child_id,
           1 as depth,
           array[n0.parent_id] as path
      from public.clinicalcode_ontologytagedge as n0
     where n0.parent_id = 3435
  union all
    select n0.parent_id,
           n0.child_id,
           n1.depth + 1 as depth,
           path || n0.parent_id as path
      from public.clinicalcode_ontologytagedge as n0,
           descendants as n1
     where n0.parent_id = n1.child_id
       and n0.parent_id <> all(n1.path)
  ),
  node_path as (
    select unnest(array[id]) as id
      from (
        select path || array[3564]::bigint[],
               depth
          from descendants
         where child_id = 3564
           and depth <= 20
         limit 1
      ) as x(id)
  )

select *
 from node_path;



-------------------------------------------------------------

-- Compute path(s) for a set of node(s)

with
  recursive descendants(parent_id, child_id, depth, path) as (
    select n0.parent_id,
           n0.child_id,
           1 as depth,
           array[n0.parent_id] as path
      from public.clinicalcode_ontologytagedge as n0
     where n0.parent_id = any(array[1, 3435])
     union all
    select n0.parent_id,
           n0.child_id,
           n1.depth + 1 as depth,
           path || n0.parent_id as path
      from public.clinicalcode_ontologytagedge as n0,
           descendants as n1
     where n0.parent_id = n1.child_id
       and n0.parent_id <> all(n1.path)
  )

select 
       child.id as id,
       path || array[child.id]::bigint[],
       depth
  from (
    select id
      from public.clinicalcode_ontologytag
     where id = any(array[4, 3564])
  ) as child,
       descendants as paths
 where paths.child_id = child.id
   and depth <= 20



-------------------------------------------------------------

-- Compute ancestor tree from a set of node(s)

with
  recursive ancestors(parent_id, child_id, depth, path) as (
    select n0.parent_id,
           n0.child_id,
           1 as depth,
           array[n0.parent_id, n0.child_id] as path
      from public.clinicalcode_ontologytagedge as n0
      left outer join public.clinicalcode_ontologytagedge as n1
        on n0.parent_id = n1.child_id
     where n0.child_id = any(array[4, 45021])
     union
    select n2.parent_id,
           ancestors.child_id,
           ancestors.depth + 1 as depth,
           n2.parent_id || ancestors.path
      from ancestors
      join public.clinicalcode_ontologytagedge as n2
        on n2.child_id = ancestors.parent_id
  )

select p0.child_id,
       p0.path
  from ancestors as p0
  join
    (
      select child_id,
             max(depth) as max_depth
        from ancestors
       group by child_id
    ) as lim
    on lim.child_id = p0.child_id
   and lim.max_depth = p0.depth;



-------------------------------------------------------------

-- Compute ancestor tree data

with
  recursive ancestry(parent_id, child_id, depth, path) as (
    select n0.parent_id,
           n0.child_id,
           1 as depth,
           array[n0.parent_id, n0.child_id] as path
      from public.clinicalcode_ontologytagedge as n0
      left outer join public.clinicalcode_ontologytagedge as n1
        on n0.parent_id = n1.child_id
     where n0.child_id = any(array[4, 45021])
     union
    select n2.parent_id,
           ancestry.child_id,
           ancestry.depth + 1 as depth,
           n2.parent_id || ancestry.path
      from ancestry
      join public.clinicalcode_ontologytagedge as n2
        on n2.child_id = ancestry.parent_id
  ),
  ancestors as (
    select p0.child_id,
          p0.path
      from ancestry as p0
      join (
            select child_id,
                   max(depth) as max_depth
              from ancestry
            group by child_id
          ) as lim
        on lim.child_id = p0.child_id
       and lim.max_depth = p0.depth
  ),
  objects as (
	  select selected.child_id,
           jsonb_build_object(
              'id', nodes.id,
              'label', nodes.name,
              'isLeaf', case when count(edges1.child_id) < 1 then True else False end,
              'isRoot', case when max(edges0.parent_id) is NULL then True else False end,
              'type_id', nodes.type_id,
              'atlas_id', nodes.atlas_id,
              'child_count', count(edges1.child_id)
           ) as tree
        from (
            select id,
                  child_id
              from ancestors,
                  unnest(path) as id
             group by id, child_id
          ) as selected
        join public.clinicalcode_ontologytag as nodes
          on nodes.id = selected.id
        left outer join public.clinicalcode_ontologytagedge as edges0
          on nodes.id = edges0.child_id
        left outer join public.clinicalcode_ontologytagedge as edges1
          on nodes.id = edges1.parent_id
       group by selected.child_id, nodes.id
  )

select ancestor.child_id,
	     ancestor.path,
	     json_agg(obj.tree) as dataset
  from ancestors as ancestor
  join objects as obj
    on obj.child_id = ancestor.child_id
 group by ancestor.child_id, ancestor.path;
