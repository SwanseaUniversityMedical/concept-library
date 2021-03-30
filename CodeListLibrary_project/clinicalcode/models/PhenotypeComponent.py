'''
    ---------------------------------------------------------------------------
    COMPONENT MODEL

    Model for the concept components.
    ---------------------------------------------------------------------------
'''

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from .TimeStampedModel import TimeStampedModel
from django.contrib.postgres.fields import JSONField
from .Phenotype import Phenotype

class PhenotypeComponent(TimeStampedModel):
    '''
        Component of a phenotype.
        Each component contains data about the arbitrary tables attached
        (e.g. from HDRUK portal).
    '''
    
    phenotype = models.ForeignKey(Phenotype)
    group_name = models.CharField(max_length=250)                   # e.g primary care/ secondary care, ...
    table_name = models.CharField(max_length=250, null=True, blank=True)                   # name of the arbitrary table
    file_name = models.CharField(max_length=250, null=True, blank=True)                   # name of the csv file
    table_description = models.CharField(max_length=1000, null=True, blank=True)           # description of the arbitrary table
    concept_ids = JSONField()                                       # id/version of used concepts
    table_data = JSONField()                                        # table header/body (rows/columns)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotypecomponents_created")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotypecomponents_modified")
    
    history = HistoricalRecords()

    class Meta:
        ordering = ('created',)

    def __str__(self):
        return self.name
