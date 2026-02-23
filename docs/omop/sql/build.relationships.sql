alter table public.clinicalcode_omoprelationships
  set unlogged;

\copy public.clinicalcode_omoprelationships(code0_id, code1_id, relationship, valid_start_date, valid_end_date, invalid_reason)
 from '../path/to/OMOP/packages/DATASO~1/CONCEP~1.CSV'
 with (
  FORMAT csv,
  DELIMITER ',',
  HEADER,
  ENCODING 'UTF8',
  QUOTE '"',
  ESCAPE '"'
);

alter table public.clinicalcode_omoprelationships
  set logged;
