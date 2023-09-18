from django.db import models
from django.contrib.postgres.indexes import GinIndex

class READ_CD_CV2_SCD(models.Model):
    read_code = models.CharField(max_length=5, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    pref_term_30 = models.CharField(max_length=30, null=True, blank=True)
    pref_term_60 = models.CharField(max_length=60, null=True, blank=True)
    pref_term_198 = models.CharField(max_length=198, null=True, blank=True)
    icd9_code = models.CharField(max_length=20, null=True, blank=True)
    icd9_code_def = models.CharField(max_length=2, null=True, blank=True)
    icd9_cm_code = models.CharField(max_length=20, null=True, blank=True)
    icd9_cm_code_def = models.CharField(max_length=2, null=True, blank=True)
    opcs_4_2_code = models.CharField(max_length=20, null=True, blank=True)
    opcs_4_2_code_def = models.CharField(max_length=2, null=True, blank=True)
    speciality_flag = models.CharField(max_length=10, null=True, blank=True)
    status_flag = models.CharField(max_length=1, null=True, blank=True)
    language_code = models.CharField(max_length=2, null=True, blank=True)
    source_file_name = models.CharField(max_length=255, null=True, blank=True)
    in_source_data = models.BigIntegerField(null=True, blank=True)
    import_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    is_latest = models.BigIntegerField(null=True, blank=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    avail_from_dt = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(
                name='readv2_code_ln_gin_idx',
                fields=['read_code'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='readv2_defn_ln_gin_idx',
                fields=['description'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='readv2_desc_ln_gin_idx',
                fields=['pref_term_30'],
                opclasses=['gin_trgm_ops']
            ),
        ]
