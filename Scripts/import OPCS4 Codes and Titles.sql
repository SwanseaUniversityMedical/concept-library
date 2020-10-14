
-- DROP TABLE public.clinicalcode_staging_codes_and_titles;
TRUNCATE TABLE public.clinicalcode_opcs4_codes_and_titles;

CREATE TABLE public.clinicalcode_staging_opcs4_codes_and_titles
(
  code_with_decimal character varying(50),
  code_without_decimal character varying(50),
  title character varying(255),
  opcs_version numeric(10,4),
  import_date character varying(50),
  created_date character varying(50),
  effective_from character varying(50),
  effective_to character varying(50),
  avail_from_dt character varying(50)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.clinicalcode_staging_opcs4_codes_and_titles
  OWNER TO clluser;

psql .......
copy public.clinicalcode_staging_opcs4_codes_and_titles(code_with_decimal, code_without_decimal, title, opcs_version, 
       import_date, created_date, effective_from, effective_to, avail_from_dt
) FROM 'C:\Users\<user>\Codes\OPCS4_CODES_AND_TITLES_201712121110.csv' DELIMITER ',' csv header encoding 'windows-1251';

INSERT INTO public.clinicalcode_opcs4_codes_and_titles(
            code_with_decimal, code_without_decimal, title, opcs_version, 
       import_date, created_date, effective_from, effective_to, avail_from_dt)
SELECT code_with_decimal, code_without_decimal, title, opcs_version, 
       to_date(import_date, 'YYYY-MM-DD'), to_date(created_date, 'YYYY-MM-DD'), to_date(effective_from, 'YYYY-MM-DD'), to_timestamp(effective_to, 'YYYY-MM-DD'), 
       to_timestamp(avail_from_dt, 'YYYY-MM-DD')
  FROM public.clinicalcode_staging_opcs4_codes_and_titles;


DROP TABLE public.clinicalcode_staging_opcs4_codes_and_titles;
  