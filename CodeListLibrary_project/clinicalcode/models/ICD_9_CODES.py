from django.db import models
from django.contrib.postgres.indexes import GinIndex

class ICD_9_CODES(models.Model):
    code = models.CharField(max_length=50, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    field = models.CharField(max_length=255, null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    import_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    avail_from_dt = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(
                name='icd9_code_ln_gin_idx',
                fields=['code'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='icd9_desc_ln_gin_idx',
                fields=['description'],
                opclasses=['gin_trgm_ops']
            ),
        ]
