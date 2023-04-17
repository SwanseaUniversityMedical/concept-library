'''
    Concept Model

    A Concept contains a list of Components specified by inclusion/exclusion.
'''
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.template.defaultfilters import default
from simple_history.models import HistoricalRecords

from ..permissions import Permissions
from .CodingSystem import CodingSystem
from .TimeStampedModel import TimeStampedModel


class Concept(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="concepts_created")
    author = models.CharField(max_length=1000)
    entry_date = models.DateField()
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="concepts_modified" )  # user of the person who modified this row.
    validation_performed = models.BooleanField(null=True, default=False)  # Was there any clinical validation of this concept?  1=yes 0=no
    validation_description = models.TextField(null=True, blank=True)  # Description of Validation (think about structure of this)
    publication_doi = models.CharField(max_length=100)  # DOI of publication
    publication_link = models.URLField(max_length=1000)  # http link to pub
    secondary_publication_links = models.TextField(null=True, blank=True)
    paper_published = models.BooleanField(null=True, default=False)  # Has a paper been published with these codes? 1=yes 0=no
    source_reference = models.CharField(max_length=250)  # Was this code list from another source?  Reference here.
    citation_requirements = models.TextField(null=True, blank=True)  # Any request for citation requirements to be honoured
    coding_system = models.ForeignKey(CodingSystem, on_delete=models.SET_NULL, related_name="concepts", null=True, blank=True)
    is_deleted = models.BooleanField(null=True, default=False)
    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="concepts_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="concepts_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    
    owner_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.EDIT)
    group_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)
    world_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)

    tags = ArrayField(models.IntegerField(), blank=True, null=True)
    collections = ArrayField(models.IntegerField(), blank=True, null=True)
    code_attribute_header = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    friendly_id = models.CharField(max_length=50, default='', editable=False)
    
    ''' To be removed once Concept is cleaned up in V2 '''
    is_legacy = models.BooleanField(default=True)
    ''' ---------------------------------------------- '''

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        self.friendly_id = 'C' + str(self.id)
        super(Concept, self).save(*args, **kwargs)

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
