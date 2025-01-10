from django.db import models
from django.contrib.postgres.indexes import GinIndex

class ICD10CA_CODES(models.Model):
    code = models.CharField(max_length=64, null=True, blank=True)
    description = models.CharField(max_length=128, null=True, blank=True)
    long_desc = models.CharField(max_length=255, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            GinIndex(
                name='icd10ca_cd_ln_gin_idx',
                fields=['code'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='icd10ca_lds_ln_gin_idx',
                fields=['description'],
                opclasses=['gin_trgm_ops']
            ),
        ]
