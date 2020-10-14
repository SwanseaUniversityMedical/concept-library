from django.db import models


class READ_CD_CV3_TERMS_SCD(models.Model):
    term_id = models.CharField(max_length=5, null=True, blank=True)
    term_status = models.CharField(max_length=1, null=True, blank=True)
    term_30 = models.CharField(max_length=30, null=True, blank=True)
    term_60 = models.CharField(max_length=60, null=True, blank=True)
    term_198 = models.CharField(max_length=198, null=True, blank=True)
    in_source_data = models.BigIntegerField(null=True, blank=True)
    import_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    is_latest = models.BigIntegerField(null=True, blank=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    avail_from_dt = models.DateTimeField(null=True, blank=True)
