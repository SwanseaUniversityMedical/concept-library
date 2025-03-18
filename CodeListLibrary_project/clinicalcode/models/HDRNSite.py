from django.db import models

from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNSite(TimeStampedModel):
	"""
	HDRN Institution Sites 
	"""
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=True, null=False, blank=False)
	description = models.TextField(null=True, blank=True)
	metadata = models.JSONField(blank=True, null=True)

	def __str__(self):
		return self.name
