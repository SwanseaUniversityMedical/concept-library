import datetime
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords

from ..permissions import Permissions
from .DataSource import DataSource
from .TimeStampedModel import TimeStampedModel


class Phenotype(TimeStampedModel):
    """
        Phenotype Model
        Representation of a Phenotype imported from the HDR UK Gateway.
    """
    
    id = models.CharField(primary_key=True, editable=False, max_length=50)
    # Metadata (imported from HDR UK):
    name = models.CharField(max_length=250)
    layout = models.CharField(max_length=250)
    phenotype_uuid = models.CharField(max_length=250, null=True, blank=True)  # Unique ID for the phenotype on HDR UK platform
    type = models.CharField(max_length=250)
    validation_performed = models.BooleanField(null=True, default=False)  # Was there any clinical validation of this phenotype?  1=yes 0=no
    validation = models.TextField(null=True, blank=True)
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
    secondary_publication_links = models.TextField(null=True, blank=True)
    implementation = models.TextField(null=True, blank=True)
    source_reference = models.CharField(max_length=250)  # Was this code list from another source?  Reference here.
    citation_requirements = models.TextField(null=True, blank=True)  # Any request for citation requirements to be honoured

    phenoflowid = models.CharField(max_length=100, null=True, blank=True)  # ID to link to PhenoFlow

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_updated")
    is_deleted = models.BooleanField(null=True, default=False)

    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotype_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)

    owner_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.EDIT)
    group_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)
    world_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)

    tags = ArrayField(models.IntegerField(), blank=True, null=True) 
    collections = ArrayField(models.IntegerField(), blank=True, null=True) 
    clinical_terminologies = ArrayField(models.IntegerField(), blank=True, null=True)  # coding systems
    publications = ArrayField(models.CharField(max_length=500), blank=True, null=True)

    data_sources = ArrayField(models.IntegerField(), blank=True, null=True) 

    history = HistoricalRecords()


    def save(self, *args, **kwargs):
        count = Phenotype.objects.extra(
            select={
                'true_id': '''CAST(SUBSTRING(id, 3, LENGTH(id)) AS INTEGER)'''
            }
        ).order_by('-true_id', 'id').first()

        if count and count.true_id:
            count = count.true_id + 1
        else:
            count = 1

        if not self.id:
            self.id = "PH" + str(count)

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
