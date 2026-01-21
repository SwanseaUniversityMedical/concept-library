from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.indexes import GinIndex

class StandardFlag(models.TextChoices):
	"""
	See `standard_concept` column of `CONCEPT` table found in `OHDSI docs`_.

	.. _OHDSI docs: https://www.ohdsi.org/web/wiki/doku.php?id=documentation:cdm:concept
	"""
	STANDARD = 'S', _('Standard Concept')
	CLASSIFICATION = 'C', _('Classification Concept')

class InvalidFlag(models.TextChoices):
	"""
	See `invalid_reason` column of `CONCEPT` table found in `OHDSI docs`_.

	.. _OHDSI docs: https://www.ohdsi.org/web/wiki/doku.php?id=documentation:cdm:concept
	"""
	DEPRECATED = 'D', _('Deprecated')
	UPGRADED = 'U', _('Upgraded')

class OMOP_CODES(models.Model):
		"""
		Represents a standardised `OMOP`_ code from its Common Data Model, related to :model:`clinicalcode.CodingSystem`.

		Version
		-------
		Vocabulary version: `v20250827`
		
		Reference
		---------
		See `OHDSI Single-page docs`_.

		Mapping
		----------
		| Attribute            | Table->Column                    |
		|:---------------------|:---------------------------------|
		| `code`               | `CONCEPT->concept_id`            |
		| `description`        | `CONCEPT->concept_name`          |
		| `is_code`            | `N/A`                            |
		| `is_valid`           | `N/A`                            |
		| `standard_concept`   | `CONCEPT->standard_concept`      |
		| `coding_name`        | `N/A`                            |
		| `coding_system_id`   | `N/A`                            |
		| `domain_name`        | `CONCEPT->domain_id`             |
		| `class_name`         | `CONCEPT->concept_class_id`      |
		| `vocabulary_name`    | `CONCEPT->vocabulary_id`         |
		| `vocabulary_code`    | `CONCEPT->concept_code`          |
		| `vocabulary_version` | `VOCABULARY->vocabulary_version` |
		| `valid_start_date`   | `CONCEPT->valid_start_date`      |
		| `valid_end_date`     | `CONCEPT->valid_end_date`        |
		| `invalid_reason`     | `CONCEPT->invalid_reason`        |
		| `created`            | `N/A`                            |
		| `modified`           | `N/A`                            |

		.. _OMOP: https://www.ohdsi.org/data-standardization/
		.. _OHDSI Single-page docs: https://www.ohdsi.org/web/wiki/doku.php?id=documentation:cdm:single-page
		"""
		id = models.BigAutoField(auto_created=True, primary_key=True)
		code = models.CharField(max_length=64, null=True, blank=True, unique=True, default='')
		description = models.CharField(max_length=256, null=True, blank=True, default='')
		is_code = models.BooleanField(null=False, default=True)
		is_valid = models.BooleanField(null=False, default=True)
		standard_concept = models.CharField(
			# 'S', 'C' or NULL
			null=True,
			blank=True,
			choices=StandardFlag.choices,
			default=None,
			max_length=1,
		)
		coding_name = models.CharField(max_length=256, null=True, blank=True, default='')
		coding_system = models.ForeignKey(
			'clinicalcode.CodingSystem',
			on_delete=models.SET_NULL,
			null=True,
			blank=True,
			default=None,
			related_name='omop_code'
		)
		domain_name = models.CharField(max_length=256, null=True, blank=True, default='')
		class_name = models.CharField(max_length=256, null=True, blank=True, default='')
		vocabulary_name = models.CharField(max_length=64, null=True, blank=True, default='')
		vocabulary_code = models.CharField(max_length=64, null=True, blank=True, default='')
		vocabulary_version = models.CharField(max_length=256, null=True, blank=True, default='')
		valid_start_date = models.DateField(null=True, blank=True)
		valid_end_date = models.DateField(null=True, blank=True)
		invalid_reason = models.CharField(
			# 'D', 'U' or NULL
			null=True,
			blank=True,
			choices=InvalidFlag.choices,
			default=None,
			max_length=1,
		)
		created = models.DateTimeField(auto_now_add=True, editable=True)
		modified = models.DateTimeField(auto_now_add=True, editable=True)

		class Meta:
			ordering = ('id',)
			indexes = [
				models.Index(fields=['id']),
				models.Index(fields=['created']),
				GinIndex(
					name='omop_cd_trgm_idx',
					fields=['code'],
					opclasses=['gin_trgm_ops']
				),
				GinIndex(
						name='omop_desc_trgm_idx',
						fields=['description'],
						opclasses=['gin_trgm_ops']
				),
				GinIndex(
					name='omop_cs_trgm_idx',
					fields=['coding_name'],
					opclasses=['gin_trgm_ops']
				),
				GinIndex(
						name='omop_vscd_trgm_idx',
						fields=['vocabulary_code'],
						opclasses=['gin_trgm_ops']
				),
			]
