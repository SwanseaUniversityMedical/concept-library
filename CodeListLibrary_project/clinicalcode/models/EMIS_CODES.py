from django.db import models


class EMIS_CODES(models.Model):
    code = models.CharField(max_length=50, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    field = models.CharField(max_length=255, null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    import_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    avail_from_dt = models.DateField(null=True, blank=True)