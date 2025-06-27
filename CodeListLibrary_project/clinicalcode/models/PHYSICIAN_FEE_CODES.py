from django.db import models
from django.contrib.postgres.indexes import GinIndex

class PHYSICIAN_FEE_CODES(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True)
    code = models.CharField(max_length=64, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            GinIndex(
                name='hpfc_cd_ln_gin_idx',
                fields=['code'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='hpfc_lds_ln_gin_idx',
                fields=['description'],
                opclasses=['gin_trgm_ops']
            ),
        ]
