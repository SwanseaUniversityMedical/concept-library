from django.db import models
from django.contrib.postgres.indexes import GinIndex

class ATCDDD_CODES(models.Model):
    code = models.CharField(max_length=64, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    ddd = models.CharField(max_length=64, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=255, null=True, blank=True)
    administration_route = models.CharField(max_length=64, null=True, blank=True)
    note = models.CharField(max_length=255, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            GinIndex(
                name='atcddd_cd_ln_gin_idx',
                fields=['code'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='atcddd_lds_ln_gin_idx',
                fields=['description'],
                opclasses=['gin_trgm_ops']
            ),
        ]
