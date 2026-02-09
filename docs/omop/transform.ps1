<# Export reformatted OMOP files #>
Get-ChildItem "./path/to/files" -Filter *.csv `
| Foreach-Object {
  Import-Csv -Path $_.FullName -Delimiter "`t" | Export-Csv -Path '.project/out/VOCABULARY.csv' -Encoding UTF8 -NoTypeInformation
}

<# Export omop.relationships.csv #>
Import-CSV `
    -Path 'CONCEPT_RELATIONSHIP.csv' `
    -Header "code0_id","code1_id","relationship","valid_start_date","valid_end_date","invalid_reason" `
  | select -skip 1 `
  | Foreach-Object {
    $_.'valid_start_date' = $($_.'valid_start_date' -replace '(?<year>\d{4})(?<month>\d{2})(?<day>\d{2})', '${year}-${month}-${day}')
    $_.'valid_end_date' = $($_.'valid_end_date' -replace '(?<year>\d{4})(?<month>\d{2})(?<day>\d{2})', '${year}-${month}-${day}')
    $_
  } `
  | Export-CSV -Path 'omop.relationships.csv' -Encoding UTF8 -NoTypeInformation
