from glob import glob
from enum import StrEnum

import os
import re
import polars as pl

# NOTE:
# 	[!] Use the vocabulary found within `.resources/bundles/Concept Bundle -- vocabulary_download_v5_{2c1bc99a-c11f-4bc7-a096-8fefe0ce251d}_1768389516543.zip`

# NOTE:
# 	[!] Vocab version: v20250827
# 	[!] Athena version: 1.15.5.56.250901.1005

class Paths(StrEnum):
	Data = './packages/datasources'
	Mapping = './.project/mappings'
	Phenotypes = './.project/phenotypes'

class Config(object):
	cs_names = pl.Enum([
		'ICD9 codes',
		'ICD10 codes',
		'OXMIS codes',
		'OPCS4 codes',
		'Read codes v2',
		'SNOMED CT codes',
	])

	cs_groups = {
		'ICD9 codes': ['ICD9CM', 'ICD9Proc'],
		'ICD10 codes': ['ICD10', 'ICD10CM', 'ICD10GM', 'ICD10PCS'],
		'OXMIS codes': ['OXMIS', 'Read'],
		'OPCS4 codes': ['OPCS4'],
		'Read codes v2': ['Read'],
		'SNOMED CT codes': ['SNOMED'],
	}

	@classmethod
	def resolve_pheno(cls, query, as_list=False, default=None):
		item = re.match(r'^PH(\d+)/(\d+)$', query)
		if item is not None:
			fname = 'PH%s_ver_%s.csv' % (item.group(1), item.group(2))
			return [fname] if as_list else fname
		return default

	@classmethod
	def build_path(cls, root, *args):
		base = None
		if isinstance(root, Paths):
			root = root.value

		match root:
			case 'data':
				base = Paths.Data.value
			case 'mapping':
				base = Paths.Mapping.value
			case 'phenotypes':
				if len(args) == 2:
					chn, trg, *_ = args
					trg = Config.resolve_pheno(trg, as_list=True)
					if isinstance(trg, list):
						base = os.path.join(Paths.Phenotypes.value, chn)
						args = trg

				if base is None:
					base = root
			case 'phenotypes/multi':
				base = os.path.join(Paths.Phenotypes.value, 'multi')
				args = Config.resolve_pheno(args[0], as_list=True, default=args)
			case 'phenotypes/single':
				base = os.path.join(Paths.Phenotypes.value, 'single')
				args = Config.resolve_pheno(args[0], as_list=True, default=args)
			case _:
				base = root

		return os.path.normpath(os.path.join(base, *args))

def build_mappings(target='single'):
	ph_schema = pl.Schema({
		'code': pl.String(),
		'description': pl.String(),
		'coding_system': Config.cs_names,
		'concept_id': pl.String(),
		'concept_version_id': pl.Int32(),
		'concept_name': pl.String(),
		'phenotype_id': pl.String(),
		'phenotype_version_id': pl.Int32(),
		'phenotype_name': pl.String(),
	})

	concepts = pl.scan_csv(
		source=Config.build_path('data', 'CONCEPT.csv'),
		has_header=True,
	)

	relationships = pl.scan_csv(
		source=Config.build_path('data', 'CONCEPT_RELATIONSHIP.csv'),
		has_header=True,
	)

	for f in glob(Config.build_path(f'phenotypes/{target}', '*.csv')):
		pheno = pl.scan_csv(
			source=f,
			schema=ph_schema,
			has_header=True,
		) \
			.collect() \
			.with_columns(
				pl.col('coding_system') \
					.replace_strict(Config.cs_groups) \
					.alias('system_mapping')
			)

		phenoid = pheno.select(
			pl.first('phenotype_id', 'phenotype_version_id')
		) \
			.map_rows(lambda x: '%s/%d' % x) \
			.to_series()[0]

		systems = pl.Series(
			pheno \
				.select(
					pl.col('system_mapping') \
						.flatten() \
						.unique()
				)
		)
		systems = ','.join(['\'%s\'' % (x,) for x in systems.to_list()])

		with pl.SQLContext(
			concepts=concepts,
			phenotype=pheno,
			relationships=relationships,
			eager=True,
		) as ctx:
			"""
				New w/ origin + coalesce
			"""
			query = '''
			with
				slim_concepts as (
					select *
						from concepts
					 where vocabulary_id in (%(vocabs)s)
				),
				mapped as (
					select
							slim_concepts.concept_id,
							slim_concepts.concept_code,
							slim_concepts.concept_name,
							slim_concepts.vocabulary_id,
							slim_concepts.invalid_reason,
							phenotype.code as origin_code,
							phenotype.coding_system as origin_system
					from phenotype
					join slim_concepts
						on phenotype.code = slim_concepts.concept_code
				 where array_contains(phenotype.system_mapping, slim_concepts.vocabulary_id)
				),
				standard as (
					select
							cc.concept_id,
							cc.concept_code,
							cc.concept_name,
							cc.vocabulary_id,
							cc.invalid_reason,
							mapped.origin_code,
							mapped.origin_system,
							mapped.concept_id as replacement_id
					  from mapped
						join relationships
							on mapped.concept_id = relationships.concept_id_1
						join concepts as cc
							on relationships.concept_id_2 = cc.concept_id
					 where cc.vocabulary_id = 'SNOMED'
					   and cc.invalid_reason = ''
						 and relationships.relationship_id = 'Maps to'
						 and relationships.invalid_reason = ''
				),
				upgradable as (
					select
							standard.concept_id,
							standard.concept_code,
							standard.concept_name,
							standard.vocabulary_id,
							standard.invalid_reason,
							standard.origin_code,
							standard.origin_system
						from standard
					 union all
					select mapped.*
						from mapped
						left join standard
							on mapped.concept_id = standard.replacement_id
						 and mapped.origin_code = standard.origin_code
					 where standard.concept_id is null
				),
				replacements as (
					select
							conc.concept_id,
							conc.concept_code,
							conc.concept_name,
							conc.vocabulary_id,
							conc.invalid_reason,
							upgradable.origin_code,
							upgradable.origin_system,
							upgradable.concept_id as replacement_id
						from upgradable
						join relationships
							on upgradable.concept_id = relationships.concept_id_1
						join concepts as conc
							on relationships.concept_id_2 = conc.concept_id
					 where regexp_like(upgradable.invalid_reason, '^(U|D)$')
						 and regexp_like(relationships.relationship_id, '^.*(replaced by|was_a from)')
						 and conc.invalid_reason = ''
						 and relationships.invalid_reason = ''
				),
				upgraded as (
					select
							replacements.concept_id,
							replacements.concept_code,
							replacements.concept_name,
							replacements.vocabulary_id,
							replacements.invalid_reason,
							replacements.origin_code,
							replacements.origin_system
						from replacements
					union all
					select upgradable.*
						from upgradable
						left join replacements
							on upgradable.concept_id = replacements.replacement_id
						 and upgradable.origin_code = replacements.origin_code
					 where replacements.concept_id is null
				)
			select *
			  from upgraded;
			''' % {
				'vocabs': systems,
			}

			codelist = ctx.execute(query)
			ctx.register('codelist', codelist)

			codelist.write_csv(
				file=Config.build_path(Paths.Phenotypes, f'out-{target}', 'codelist-%s' % (Config.resolve_pheno(phenoid))),
				quote_style='necessary'
			)

			query = '''
			select distinct on (phenotype.code)
					phenotype.phenotype_id,
					phenotype.phenotype_version_id,
					phenotype.code,
					phenotype.coding_system,
					phenotype.description
			  from phenotype
			  left join codelist
				  on phenotype.code = codelist.origin_code
				 and phenotype.coding_system = codelist.origin_system
			 where codelist.concept_id is null
			'''

			ctx \
				.execute(query) \
				.write_csv(
					file=Config.build_path(Paths.Phenotypes, f'out-{target}', 'missing-%s' % (Config.resolve_pheno(phenoid))),
					quote_style='necessary'
				)

			query = '''
			select distinct on (codelist.concept_id)
						 codelist.concept_id,
						 codelist.concept_code,
						 codelist.concept_name,
						 codelist.vocabulary_id,
						 codelist.invalid_reason,
						 ('{' || array_to_string(t.origin_codes, ', ') || '}') as origin_codes,
						 ('{' || array_to_string(t.origin_systems, ', ') || '}') as origin_systems
			  from codelist
				join (
					select f.concept_id,
								 array_agg(distinct ('"' || f.origin_code || '"')) as origin_codes,
								 array_agg(distinct ('"' || f.origin_system || '"')) as origin_systems
						from codelist as f
					 group by f.concept_id
				) t
					on t.concept_id = codelist.concept_id
			window w
			    as (partition by concept_id)
  		qualify row_number()
			   over w = 1;
			'''

			ctx \
				.execute(query) \
				.write_csv(
					file=Config.build_path('phenotypes', f'out-{target}', phenoid),
					quote_style='necessary'
				)

if __name__ == '__main__':
	build_mappings(target='single')
	build_mappings(target='multi')
