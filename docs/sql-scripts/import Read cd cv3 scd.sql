
-- DROP TABLE public.clinicalcode_staging_read_cd_cv3_terms_scd;
TRUNCATE TABLE clinicalcode_read_cd_cv3_terms_scd;
  
CREATE TABLE public.clinicalcode_staging_read_cd_cv3_terms_scd
(
  term_id character varying(5),
  term_status character varying(1),
  term_30 character varying(30),
  term_60 character varying(60),
  term_198 character varying(198),
  in_source_data bigint,
  import_date character varying(50),
  created_date character varying(50),
  is_latest bigint,
  effective_from character varying(50),
  effective_to character varying(50),
  avail_from_dt character varying(50)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.clinicalcode_staging_read_cd_cv3_terms_scd
  OWNER TO clluser;

psql ........
copy public.clinicalcode_staging_read_cd_cv3_terms_scd(term_id, term_status, term_30, term_60, term_198, in_source_data, 
       import_date, created_date, is_latest, effective_from, effective_to, 
       avail_from_dt) FROM 'C:\Users\<user>\Codes\READ_CD_CV3_TERMS_SCD_201712121109.csv' DELIMITER ',' csv header encoding 'windows-1251';

INSERT INTO public.clinicalcode_read_cd_cv3_terms_scd(term_id, term_status, term_30, term_60, term_198, in_source_data, 
       import_date, created_date, is_latest, effective_from, effective_to, 
       avail_from_dt)
SELECT term_id, term_status, term_30, term_60, term_198, in_source_data, to_timestamp(import_date, 'YYYY-MM-DD HH24:MI:SS'), 
       to_date(created_date, 'YYYY-MM-DD'), is_latest, to_date(effective_from, 'YYYY-MM-DD'), to_timestamp(effective_to, 'YYYY-MM-DD HH24:MI:SS'), 
       to_timestamp(avail_from_dt, 'YYYY-MM-DD HH24:MI:SS')
  FROM public.clinicalcode_staging_read_cd_cv3_terms_scd;

DROP TABLE public.clinicalcode_staging_read_cd_cv3_terms_scd;
  