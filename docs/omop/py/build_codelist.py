import polars as pl

# NOTE:
# 	[!] Use the vocabulary found within `.resources/bundles/Vocab Bundle -- vocabulary_download_v5_{ba86ab8a-c6a5-4bc8-9961-495466f10c05}_1768387228226.zip`

# NOTE:
# 	[!] Vocab version: v20250827
# 	[!] Athena version: 1.15.5.56.250901.1005

if __name__ == '__main__':
	schema = pl.Schema({
		'concept_id': pl.String(),
		'concept_name': pl.String(),
		'domain_id': pl.String(),
		'vocabulary_id': pl.String(),
		'concept_class_id': pl.String(),
		'standard_concept': pl.String(),
		'concept_code': pl.String(),
		'valid_start_date': pl.String(),
		'valid_end_date': pl.String(),
		'invalid_reason': pl.String(),
	})
	with pl.SQLContext(
		concepts=pl.scan_csv(
			source='./packages/datasources/CONCEPT.csv',
			schema=schema,
			has_header=True,
		),
		vocabulary=pl.scan_csv(
			source='./packages/datasources/VOCABULARY.csv',
			has_header=True,
		),
		eager=True,
	) as ctx:
		query = '''
		select
					concept_id as code,
					concept_name as description,
					(vocabulary_id != 'CDM') as is_code,
					(invalid_reason is null or invalid_reason = '') as is_valid,
					case
					 	when standard_concept is not null and standard_concept != '' then standard_concept
						else null
					end as standard_concept,
					case
						when vocabulary_id = 'Read' then 'Read codes v2'
						when vocabulary_id = 'dm+d' then 'dm+d codes'
						when vocabulary_id = 'MeSH' then 'MeSH codes'
						when vocabulary_id = 'OPCS4' then 'OPCS4 codes'
						when vocabulary_id = 'OXMIS' then 'OXMIS codes'
						when vocabulary_id = 'SNOMED' then 'SNOMED codes'
						when vocabulary_id = 'UK Biobank' then 'UKBioBank codes'
						when vocabulary_id = 'ICD9CM' then 'ICD9 codes'
						when vocabulary_id = 'ICD9Proc' then 'ICD9 codes'
						when vocabulary_id = 'ICD10' then 'ICD-10-CM codes'
						when vocabulary_id = 'ICD10CM' then 'ICD-10-CM codes'
						when vocabulary_id = 'ICD10PCS' then 'ICD-10-CM codes'
						else vocabulary_id
					end as coding_name,
					case
						when vocabulary_id = 'Read' then 5
						when vocabulary_id = 'dm+d' then 23
						when vocabulary_id = 'MeSH' then 26
						when vocabulary_id = 'OPCS4' then 7
						when vocabulary_id = 'OXMIS' then 15
						when vocabulary_id = 'SNOMED' then 9
						when vocabulary_id = 'UK Biobank' then 12
						when vocabulary_id = 'ICD9CM' then 17
						when vocabulary_id = 'ICD9Proc' then 17
						when vocabulary_id = 'ICD10' then 25
						when vocabulary_id = 'ICD10CM' then 25
						when vocabulary_id = 'ICD10PCS' then 25
						else null
					end as coding_system_id,
					domain_id as domain_name,
					concept_class_id as class_name,
					vocabulary_id as vocabulary_name,
					concept_code as vocabulary_code,
					vocabulary.vocabulary_version as vocabulary_version,
					case
						when valid_start_date is not null then date(valid_start_date, '%Y%m%d')
						else null
					end as valid_start_date,
					case
						when valid_end_date is not null and valid_end_date != '20991231' then date(valid_end_date, '%Y%m%d')
						else null
					end as valid_end_date,
					case
						when invalid_reason is not null and invalid_reason != '' then invalid_reason
						else null
					end as invalid_reason
		  from concepts
			join vocabulary
			  using (vocabulary_id)
		'''
		res = ctx.execute(query)
		res.write_csv(file='./omop.vocabulary.csv')

		with pl.Config(tbl_cols=-1):
			print(res)
			print('Row Count:', res.select(pl.len()))
