from django.contrib.auth.models import Group, User
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.postgres.fields import ArrayField

from .TimeStampedModel import TimeStampedModel

class Brand(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    logo_path = models.CharField(max_length=250)  
    index_path = models.CharField(max_length=250, blank=True, null=True)
    css_path = models.CharField(max_length=250, blank=True, null=True)
    website = models.URLField(max_length=1000, blank=True, null=True)
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,
                              null=True,
                              related_name="brand_owner")
    groups = models.ManyToManyField(Group, related_name="brand_groups")

    site_title = models.CharField(max_length=50, blank=True, null=True)
    about_menu = JSONField(blank=True, null=True)
    allowed_tabs = JSONField(blank=True, null=True)
    footer_images = JSONField(blank=True, null=True)
    collections_excluded_from_filters = ArrayField(models.IntegerField(), blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
