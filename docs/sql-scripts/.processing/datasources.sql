-- fix dsid
with
  fixes as (
    select *
      from json_to_recordset('[JSON]')
        as x(
          id bigint,
          uid text,
          dsid int
        )
  )
update public.clinicalcode_datasource as trg
   set
     uid = (case
       when src.uid is not null then src.uid
       else trg.uid
     end),
     url = (case
       when src.dsid is not null then format('https://healthdatagateway.org/en/dataset/%s', src.dsid)
       else trg.url
     end),
     datasource_id = (case
       when src.dsid is not null then src.dsid
       else trg.datasource_id 
     end)
  from fixes as src
 where trg.id = src.id;

-- check tmp valid
select ds.id, tmp.id, ds.name, tmp.name, ds.datasource_id, tmp.datasource_id, ds.description, tmp.description
  from public.clinicalcode_datasource ds
  left join public.ds_tmp tmp
    on tmp.id = ds.id
 order by ds.id asc;

-- dump
\copy (select * from public.clinicalcode_datasource order by id asc) to '%Public%/datasource.dump.csv' with (FORMAT CSV, HEADER TRUE, DELIMITER E'|', FORCE_QUOTE *, QUOTE E'`')

-- create tmp
create table public.ds_tmp (
  id bigint not null,
  name varchar(500) not null,
  description text,
  source varchar(100),
  uid varchar(250),
  url varchar(500),
  datasource_id integer,
  created_by_id integer,
  updated_by_id integer,
  created timestamp with time zone not null,
  modified timestamp with time zone not null
);

-- copy tmp
\copy public.ds_tmp(id, created, modified, name, uid, url, description, created_by_id, updated_by_id, datasource_id, source) from '%Public%/datasource.final.csv' with (FORMAT CSV, HEADER TRUE, DELIMITER E'|', QUOTE '`')

-- trunc + reset seq
truncate table public.clinicalcode_datasource restart identity;

-- insert
insert into public.clinicalcode_datasource
  select id, created, modified, name, uid, url, description, created_by_id, updated_by_id, datasource_id, source
    from public.ds_tmp
   order by id asc;

-- reset seq
select setval('clinicalcode_datasource_id_seq'::regclass, max(id))
  from public.clinicalcode_datasource; 

-- drop
drop table if exists public.ds_tmp;

-- clean
update public.clinicalcode_datasource
   set url = null
 where url ilike 'https://web.www.healthdatagateway.org/dataset/%';
