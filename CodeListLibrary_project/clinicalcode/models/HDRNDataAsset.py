from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex

from clinicalcode.models.HDRNSite import HDRNSite
from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNDataAsset(TimeStampedModel):
	"""
	HDRN Inventory Data Assets
	"""
	# Top-level
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=False, null=False, blank=False)
	description = models.TextField(null=True, blank=True)

	# Reference
	hdrn_id = models.IntegerField(null=True, blank=True)
	hdrn_uuid = models.UUIDField(primary_key=False, null=True, blank=True)

	# Metadata
	link = models.URLField(max_length=500, blank=True, null=True)
	site = models.ForeignKey(HDRNSite, on_delete=models.SET_NULL, null=True, related_name='data_assets')
	years = models.CharField(max_length=256, unique=False, null=True, blank=True)
	scope = models.TextField(null=True, blank=True)
	region = models.CharField(max_length=2048, unique=False, null=True, blank=True)
	purpose = models.TextField(null=True, blank=True)

	collection_period = models.TextField(null=True, blank=True)

	data_level = models.CharField(max_length=256, unique=False, null=True, blank=True)
	data_categories = ArrayField(models.IntegerField(), blank=True, null=True)

	class Meta:
		ordering = ('name', )
		indexes = [
			GinIndex(name='hdrn_danm_trgm_idx', fields=['name'], opclasses=['gin_trgm_ops']),
			GinIndex(name='hdrn_dadc_arr_idx', fields=['data_categories'], opclasses=['array_ops']),
		]

	def __str__(self):
		return self.name
