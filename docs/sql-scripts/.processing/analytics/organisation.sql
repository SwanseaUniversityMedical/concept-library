with
  const_org_id as (values ('1')),
  const_max_popular as (values ('5')),
  ge_vis as (
    select ge.*
      from public.clinicalcode_genericentity as ge
      join public.clinicalcode_organisation as org
        on ge.organisation_id = org.id
     where ge.organisation_id = (table const_org_id)::bigint
  ),
  hge_vis as (
    select hge.*
      from ge_vis as ge
      join public.clinicalcode_historicalgenericentity as hge
        using (id)
  ),
  ent_total as (
    select count(ge.*) as cnt
      from ge_vis as ge
  ),
  ent_created as (
    select count(ge.*) as cnt
      from ge_vis as ge
      where ge.created >= date_trunc('day', now()) - interval '30 day'
  ),
  ent_updated as (
    select count(hge.*) as cnt
      from hge_vis as hge
      where hge.updated >= date_trunc('day', now()) - interval '30 day'
  ),
  ent_views as (
    select count(req.*) as cnt
      from ge_vis as ge
      join public.easyaudit_requestevent as req
        on req.url like format('%%%s%%', ge.id)
     where req.datetime >= date_trunc('day', now()) - interval '30 day'
  ),
  ent_downloads as (
    select count(req.*) as cnt
      from ge_vis as ge
      join public.easyaudit_requestevent as req
        on req.url ~ format('api.*%s|%s.*export', ge.id, ge.id) 
     where req.datetime >= date_trunc('day', now()) - interval '30 day'
  ),
  ent_popular as (
    select
        json_agg(
          -- json_build_array(ge.id, req.cnt)
          json_build_object(
            'id', ge.id,
            'name', ge.name,
            'view_count', req.cnt
          )
          order by req.cnt desc
        ) as cnt
      from (
        select t0.id, count(t1.*) as cnt
          from ge_vis as t0
          join public.easyaudit_requestevent as t1
            on t1.url like format('%%%s%%', t0.id)
         group by t0.id
         order by cnt desc
         limit (table const_max_popular)::int
      ) as req
      join ge_vis as ge
        on req.id = ge.id
  )
select
    (select cnt from ent_total)     as total,
    (select cnt from ent_created)   as created,
    (select cnt from ent_updated)   as edited,
    (select cnt from ent_views)     as views,
    (select cnt from ent_downloads) as downloads,
    (select cnt from ent_popular)   as popular
