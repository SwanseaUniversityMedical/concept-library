
-- DROP TABLE public.clinicalcode_staging_read_cd_cv2_scd;
TRUNCATE TABLE clinicalcode_read_cd_cv2_scd;

CREATE TABLE public.clinicalcode_staging_read_cd_cv2_scd
(
  read_code character varying(5),
  pref_term_30 character varying(30),
  pref_term_60 character varying(60),
  pref_term_198 character varying(198),
  icd9_code character varying(20),
  icd9_code_def character varying(2),
  icd9_cm_code character varying(20),
  icd9_cm_code_def character varying(2),
  opcs_4_2_code character varying(20),
  opcs_4_2_code_def character varying(2),
  speciality_flag character varying(10),
  status_flag character varying(1),
  language_code character varying(2),
  source_file_name character varying(255),
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
ALTER TABLE public.clinicalcode_staging_read_cd_cv2_scd
  OWNER TO clluser;

  psql........
copy public.clinicalcode_staging_read_cd_cv2_scd(read_code, pref_term_30, pref_term_60, pref_term_198, icd9_code, 
       icd9_code_def, icd9_cm_code, icd9_cm_code_def, opcs_4_2_code, 
       opcs_4_2_code_def, speciality_flag, status_flag, language_code, 
       source_file_name, in_source_data, import_date, created_date, 
       is_latest, effective_from, effective_to, avail_from_dt) FROM 'C:\Users\david.brown\Downloads\READ_CD_CV2_SCD_201712121108.csv' DELIMITER ',' csv header encoding 'windows-1251';

INSERT INTO public.clinicalcode_read_cd_cv2_scd(read_code, pref_term_30, pref_term_60, pref_term_198, icd9_code, 
       icd9_code_def, icd9_cm_code, icd9_cm_code_def, opcs_4_2_code, 
       opcs_4_2_code_def, speciality_flag, status_flag, language_code, 
       source_file_name, in_source_data, import_date, created_date, 
       is_latest, effective_from, effective_to, avail_from_dt)
SELECT read_code, pref_term_30, pref_term_60, pref_term_198, icd9_code, 
       icd9_code_def, icd9_cm_code, icd9_cm_code_def, opcs_4_2_code, 
       opcs_4_2_code_def, speciality_flag, status_flag, language_code, 
       source_file_name, in_source_data, to_timestamp(import_date, 'YYYY-MM-DD HH24:MI:SS'), 
       to_date(created_date, 'YYYY-MM-DD'), is_latest, to_date(effective_from, 'YYYY-MM-DD'), to_timestamp(effective_to, 'YYYY-MM-DD HH24:MI:SS'), 
       to_timestamp(avail_from_dt, 'YYYY-MM-DD HH24:MI:SS')
  FROM public.clinicalcode_staging_read_cd_cv2_scd;


DROP TABLE public.clinicalcode_staging_read_cd_cv2_scd;
  