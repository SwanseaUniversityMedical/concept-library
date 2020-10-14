
-- DROP TABLE public.clinicalcode_staging_icd10_codes_and_titles_and_metadata;
TRUNCATE TABLE clinicalcode_icd10_codes_and_titles_and_metadata;

CREATE TABLE public.clinicalcode_staging_icd10_codes_and_titles_and_metadata
(
  code character varying(6),
  alt_code character varying(5),
  usage character varying(8),
  usage_uk bigint,
  description character varying(255),
  modifier_4 character varying(255),
  modifier_5 character varying(255),
  qualifiers character varying(255),
  gender_mask bigint,
  min_age bigint,
  max_age bigint,
  tree_description character varying(255),
  chapter_number bigint,
  chapter_code character varying(5),
  chapter_description character varying(255),
  category_1_code character varying(7),
  category_1_description character varying(255),
  category_2_code character varying(7),
  category_2_description character varying(255),
  category_3_code character varying(7),
  category_3_description character varying(255),
  icd_version character varying(50),
  import_date character varying(50),
  created_date character varying(50),
  effective_from character varying(50),
  effective_to character varying(50),
  avail_from_dt character varying(50)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.clinicalcode_staging_icd10_codes_and_titles_and_metadata
  OWNER TO clluser;
  
psql ..........

copy public.clinicalcode_staging_icd10_codes_and_titles_and_metadata(code, alt_code, usage, usage_uk, description, modifier_4, 
       modifier_5, qualifiers, gender_mask, min_age, max_age, tree_description, 
       chapter_number, chapter_code, chapter_description, category_1_code, 
       category_1_description, category_2_code, category_2_description, 
       category_3_code, category_3_description, icd_version, import_date, 
       created_date, effective_from, effective_to, avail_from_dt) FROM 'C:\Users\<user>\Codes\ICD10_CODES_AND_TITLES_AND_METADATA_201712121111.csv' DELIMITER ',' csv header encoding 'windows-1251';

INSERT INTO public.clinicalcode_icd10_codes_and_titles_and_metadata(code, alt_code, usage, usage_uk, description, modifier_4, 
       modifier_5, qualifiers, gender_mask, min_age, max_age, tree_description, 
       chapter_number, chapter_code, chapter_description, category_1_code, 
       category_1_description, category_2_code, category_2_description, 
       category_3_code, category_3_description, icd_version, import_date, 
       created_date, effective_from, effective_to, avail_from_dt)
SELECT code, alt_code, usage, usage_uk, description, modifier_4, 
       modifier_5, qualifiers, gender_mask, min_age, max_age, tree_description, 
       chapter_number, chapter_code, chapter_description, category_1_code, 
       category_1_description, category_2_code, category_2_description, 
       category_3_code, category_3_description, icd_version, 
  to_timestamp(import_date, 'YYYY-MM-DD HH24:MI:SS'), 
  to_date(created_date, 'YYYY-MM-DD'),
  to_date(effective_from, 'YYYY-MM-DD'),
  to_timestamp(effective_to, 'YYYY-MM-DD HH24:MI:SS'), 
  to_timestamp(avail_from_dt, 'YYYY-MM-DD HH24:MI:SS')
  FROM public.clinicalcode_staging_icd10_codes_and_titles_and_metadata;

DROP TABLE public.clinicalcode_staging_icd10_codes_and_titles_and_metadata;
  