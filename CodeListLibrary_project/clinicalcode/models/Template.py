from django.contrib.auth.models import Group, User
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.postgres.fields import ArrayField

from .TimeStampedModel import TimeStampedModel
from .Brand import Brand
from clinicalcode.constants import *
from ..entity_utils import constants

class Template(TimeStampedModel):
    '''
        Template
            @desc describes the structure of the data for that type of generic entity
                and holds statistics information e.g.
                    - count of each entity within this template
                    - count of tag/collection/datasource/coding system/

                also holds information relating to order of the layout (since JSONB does not preserve order)
                and represents the filterable fields as a hasmap to improve performance
    '''

    ''' Metadata '''
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    definition = JSONField(blank=True, null=True, default=dict)
    entity_prefix = models.CharField(editable=True, max_length=4)

    ''' Instance data '''
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="template_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="template_updated")
    history = HistoricalRecords()

    ''' Statistics '''
    entity_count = models.BigIntegerField(default=0, null=False, editable=False)
    entity_filters = ArrayField(models.CharField(max_length=500), blank=True, null=True, editable=False)
    entity_order = ArrayField(models.CharField(max_length=500), blank=True, null=True, editable=False)
    entity_statistics = JSONField(blank=True, null=True, default=dict, editable=False)

    def save(self,  *args, **kwargs):
        '''
            - Responsible for building and modifying the 'entity_filters' field
                -> Iterates through the template and collects each filterable field for easier access
            - Responsible for building and modifying the 'entity_statistics' field
                -> Iterates through the template and creates keys for filterable fields so that it can be computed during a job
        '''        
        if self.definition is not None and 'fields' in self.definition:
            filterable = []
            statistics = { }
            for field, packet in self.definition['fields'].items():
                if 'filterable' in packet and field not in filterable:
                    filterable.append(field)

                    if field not in statistics:
                        if field in self.entity_statistics:
                            statistics[field] = self.entity_statistics[field]
                        else:
                            statistics[field] = { }
            
            for field in constants.sourced_data:
                if field in self.entity_statistics:
                    statistics[field] = self.entity_statistics[field]
                else:
                    statistics[field] = { }

            self.entity_filters = filterable
            self.entity_statistics = statistics

        super(Template, self).save(*args, **kwargs)
    
    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
