create or replace function get_ontological_ancestors(node_ids bigint[])
  returns table(
    node_id bigint,
    path     bigint[]
  )
  language plpgsql as $fn$
  begin
    return query
      with recursive
        ancestors (parent_id, child_id, depth, path) as (
          select n0.parent_id,
                 n0.child_id,
                 1 as depth,
                 array[n0.parent_id, n0.child_id] as path
            from public.clinicalcode_ontologytagedge as n0
           where n0.child_id = any(node_ids)
           union all
          select n1.parent_id,
                 n0.child_id,
                 n0.depth + 1 as depth,
                 n1.parent_id || n0.path
            from ancestors as n0,
                 public.clinicalcode_ontologytagedge as n1
           where n1.child_id = n0.parent_id
        )
      select p0.child_id as node_id,
             p0.path as path
        from ancestors as p0;
  end
  $fn$;

create or replace function get_ontological_descendants(node_ids bigint[])
  returns table(
    node_id bigint,
    path     bigint[]
  )
  language plpgsql as $fn$
  begin
    return query
      with recursive
        descendants (parent_id, child_id, depth, path) as (
          select n0.parent_id,
                 n0.child_id,
                 1 as depth,
                 array[n0.parent_id] as path
            from public.clinicalcode_ontologytagedge as n0
           where n0.parent_id = any(node_ids)
           union all
          select n0.parent_id,
                 n1.child_id,
                 n0.depth + 1 as depth,
                 n1.parent_id || n0.path
            from descendants as n0,
                 public.clinicalcode_ontologytagedge as n1
           where n1.parent_id = n0.child_id
        )
      select p0.parent_id as node_id,
             p0.child_id || p0.path as path
        from descendants as p0;
  end
  $fn$;
