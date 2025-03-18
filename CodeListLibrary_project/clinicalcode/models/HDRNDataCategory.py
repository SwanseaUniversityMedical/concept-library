from django.db import models
from django.contrib.postgres.indexes import GinIndex

from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNDataCategory(TimeStampedModel):
	"""
	HDRN Data Categories (e.g. Phenotype Type)
	"""
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=False, null=False, blank=False)
	description = models.TextField(null=True, blank=True)
	metadata = models.JSONField(blank=True, null=True)

	class Meta:
		indexes = [
			GinIndex(name='hdrn_dcnm_trgm_idx', fields=['name'], opclasses=['gin_trgm_ops']),
		]

	def __str__(self):
		return self.name
