from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.contrib.auth.models import User, Group
from simple_history.models import HistoricalRecords
from django.contrib.postgres.fields import JSONField
from TimeStampedModel import TimeStampedModel
from ..permissions import Permissions
from DataSource import DataSource


class Phenotype(TimeStampedModel):
    """
        Phenotype Model

        Representation of a Phenotype imported from the HDR UK Gateway.
        Has the following additional relationships:
        - DataSource: One to Many. A phenotype can have a number of data sources.
        - ClinicalTerminology: One to Many. A phenotype can have a number of clinical terminologies.
    """

    # Metadata (imported from HDR UK):
    title = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    layout = models.CharField(max_length=250)
    phenotype_id = models.CharField(max_length=250)   # Unique ID for the phenotype on HDR UK platform
    type = models.CharField(max_length=250)
    validation_performed = models.NullBooleanField()  # Was there any clinical validation of this phenotype?  1=yes 0=no
    validation = models.CharField(max_length=3000)
    valid_event_data_range_start = models.DateField()
    valid_event_data_range_end = models.DateField()
    sex = models.CharField(max_length=50)
    author = models.CharField(max_length=250)
    status = models.CharField(max_length=50)
    hdr_created_date = models.DateField()
    hdr_modified_date = models.DateField()
    description = models.TextField()
    concept_informations = JSONField()
    publication_doi = models.CharField(max_length=100)  # DOI of publication
    publication_link = models.URLField(max_length=1000)  # http link to pub
    secondary_publication_links = models.CharField(max_length=3000, null=True, blank=True)
    implementation = models.CharField(max_length=3000, null=True, blank=True)
    source_reference = models.CharField(max_length=250)  # Was this code list from another source?  Reference here.
    citation_requirements = models.CharField(max_length=250)  # Any request for citation requirements to be honoured
    
    phenoflowid = models.CharField(max_length=100, null=True, blank=True)  # ID to link to PhenoFlow
    
    #data_sources = models.ManyToManyField(DataSource)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_updated")
    is_deleted = models.NullBooleanField()
    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, related_name="phenotype_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    owner_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.EDIT)
    group_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)
    world_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)

    tags = ArrayField(models.IntegerField(), blank=True, null=True)  #default=list
    clinical_terminologies = ArrayField(models.IntegerField(), blank=True, null=True)  #default=list
    publications = models.CharField(max_length=3000, null=True, blank=True)
    
    history = HistoricalRecords()

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name
