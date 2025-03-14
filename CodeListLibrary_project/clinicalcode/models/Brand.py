from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

from .TimeStampedModel import TimeStampedModel

class Brand(TimeStampedModel):
    id = models.AutoField(primary_key=True)

    # Brand metadata
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(max_length=1000, blank=True, null=True)

    # Brand appearance
    site_title = models.CharField(max_length=50, blank=True, null=True)
    logo_path = models.CharField(max_length=250)
    index_path = models.CharField(max_length=250, blank=True, null=True)

    # Brand administration
    admins = models.ManyToManyField(User, related_name='administered_brands')

    # Brand overrides
    #   - e.g. entity name override ('Concept' instead of 'Phenotype' _etc_ for HDRN brand)
    overrides = models.JSONField(blank=True, null=True)

    # Brand organisation controls
    org_user_managed = models.BooleanField(default=False)

    # Brand menu targets
    about_menu = models.JSONField(blank=True, null=True)
    allowed_tabs = models.JSONField(blank=True, null=True)
    footer_images = models.JSONField(blank=True, null=True)
    collections_excluded_from_filters = ArrayField(models.IntegerField(), blank=True, null=True)

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
