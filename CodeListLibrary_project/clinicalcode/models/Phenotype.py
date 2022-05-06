from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from simple_history.models import HistoricalRecords

from ..permissions import Permissions
from .DataSource import DataSource
from .TimeStampedModel import TimeStampedModel


class Phenotype(TimeStampedModel):
    """
        Phenotype Model

        Representation of a Phenotype imported from the HDR UK Gateway.
        Has the following additional relationships:
        - DataSource: One to Many. A phenotype can have a number of data sources.
    """

    # Metadata (imported from HDR UK):
    title = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    layout = models.CharField(max_length=250)
    phenotype_uuid = models.CharField(max_length=250)  # Unique ID for the phenotype on HDR UK platform
    type = models.CharField(max_length=250)
    validation_performed = models.NullBooleanField()  # Was there any clinical validation of this phenotype?  1=yes 0=no
    validation = models.CharField(max_length=3000)
    valid_event_data_range = models.CharField(max_length=250, null=True, blank=True)
    #     valid_event_data_range_start = models.DateField()
    #     valid_event_data_range_end = models.DateField()
    sex = models.CharField(max_length=50)
    author = models.CharField(max_length=1000)
    status = models.CharField(max_length=50)
    hdr_created_date = models.CharField(max_length=50, null=True, blank=True)
    hdr_modified_date = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField()
    concept_informations = JSONField()
    publication_doi = models.CharField(max_length=100)  # DOI of publication
    publication_link = models.URLField(max_length=1000)  # http link to pub
    secondary_publication_links = models.CharField(max_length=3000, null=True, blank=True)
    implementation = models.TextField(null=True, blank=True)
    source_reference = models.CharField(max_length=250)  # Was this code list from another source?  Reference here.
    citation_requirements = models.CharField(max_length=250)  # Any request for citation requirements to be honoured

    phenoflowid = models.CharField(max_length=100, null=True, blank=True)  # ID to link to PhenoFlow

    #data_sources = models.ManyToManyField(DataSource)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_updated")
    is_deleted = models.NullBooleanField()
    #is_approved = models.NullBooleanField(default=False)
    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)

    owner_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES,
                                       default=Permissions.EDIT)
    group_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES,
                                       default=Permissions.NONE)
    world_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES,
                                       default=Permissions.NONE)

    tags = ArrayField(models.IntegerField(), blank=True, null=True)  #default=list
    clinical_terminologies = ArrayField(models.IntegerField(), blank=True, null=True)  # coding systems
    publications = ArrayField(models.CharField(max_length=500), blank=True, null=True)

    friendly_id = models.CharField(max_length=50, default='', editable=False)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        self.friendly_id = 'PH' + str(self.id)
        super(Phenotype, self).save(*args, **kwargs)

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
