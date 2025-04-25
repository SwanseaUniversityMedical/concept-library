-- improved perf. counting coding systems
do
$bd$
declare
  _query text;
  _ref text;
  _row_cnt int;
  _record json;
  _coding_tables json;

  _result jsonb := '[]'::jsonb;
  _cursor constant refcursor := '_cursor';
begin
  select
      json_agg(json_build_object(
        'name', coding.name,
        'value', coding.id,
        'table_name', coding.table_name
      )) as tbl
    from public.clinicalcode_codingsystem as coding
    into _coding_tables;

  for _record, _ref
    in select obj, obj->>'table_name'::text from json_array_elements(_coding_tables) obj
  loop
    if exists(select 1 from information_schema.tables where table_name = _ref) then
      _query := format('select count(*) from %I', _ref);
      execute _query into _row_cnt;
    else
      _row_cnt = 0;
    end if;

    _result = _result || format(
      '[{
        "name": "%s",
        "value": %s,
        "table_name": "%s",
        "code_count": %s,
        "can_search": %s
      }]',
      _record->>'name'::text,
      _record->>'value'::text,
      _record->>'table_name'::text,
      _row_cnt::int,
      (_row_cnt::int > 0)::text
    )::jsonb;
  end loop;

  _query := format('select %L::jsonb as res', _result::text);
  open _cursor for execute _query;
end;
$bd$;
fetch all from _cursor;
