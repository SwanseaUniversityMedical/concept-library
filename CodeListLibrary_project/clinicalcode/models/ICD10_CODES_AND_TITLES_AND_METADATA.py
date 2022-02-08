from django.db import models


class ICD10_CODES_AND_TITLES_AND_METADATA(models.Model):
    code = models.CharField(max_length=6, null=True, blank=True)
    alt_code = models.CharField(max_length=5, null=True, blank=True)
    usage = models.CharField(max_length=8, null=True, blank=True)
    usage_uk = models.BigIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    modifier_4 = models.CharField(max_length=255, null=True, blank=True)
    modifier_5 = models.CharField(max_length=255, null=True, blank=True)
    qualifiers = models.CharField(max_length=255, null=True, blank=True)
    gender_mask = models.BigIntegerField(null=True, blank=True)
    min_age = models.BigIntegerField(null=True, blank=True)
    max_age = models.BigIntegerField(null=True, blank=True)
    tree_description = models.CharField(max_length=255, null=True, blank=True)
    chapter_number = models.BigIntegerField(null=True, blank=True)
    chapter_code = models.CharField(max_length=5, null=True, blank=True)
    chapter_description = models.CharField(max_length=255,
                                           null=True,
                                           blank=True)
    category_1_code = models.CharField(max_length=7, null=True, blank=True)
    category_1_description = models.CharField(max_length=255,
                                              null=True,
                                              blank=True)
    category_2_code = models.CharField(max_length=7, null=True, blank=True)
    category_2_description = models.CharField(max_length=255,
                                              null=True,
                                              blank=True)
    category_3_code = models.CharField(max_length=7, null=True, blank=True)
    category_3_description = models.CharField(max_length=255,
                                              null=True,
                                              blank=True)
    icd_version = models.CharField(max_length=50, null=True, blank=True)
    import_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    avail_from_dt = models.DateField(null=True, blank=True)
