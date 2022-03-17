from django.db import models


class OPCS4_CODES_AND_TITLES(models.Model):
    code_with_decimal = models.CharField(max_length=50, null=True, blank=True)
    code_without_decimal = models.CharField(max_length=50,
                                            null=True,
                                            blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    opcs_version = models.DecimalField(max_digits=10,
                                       decimal_places=4,
                                       null=True,
                                       blank=True)
    import_date = models.DateField(null=True, blank=True)
    created_date = models.DateField(null=True, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    avail_from_dt = models.DateField(null=True, blank=True)
