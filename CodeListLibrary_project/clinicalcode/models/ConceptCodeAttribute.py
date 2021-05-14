'''
    ---------------------------------------------------------------------------
    COMPONENT MODEL

    Model for the concept components.
    ---------------------------------------------------------------------------
'''

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from .Concept import Concept
from .TimeStampedModel import TimeStampedModel
from django.contrib.postgres.fields import ArrayField

class ConceptCodeAttribute(TimeStampedModel):
    '''
        Store attributes of codes in a concept.
        This is a lookup not related to the concept components.
    '''

    concept = models.ForeignKey(Concept)
    code = models.CharField(max_length=20)  # A Single Code
    attributes = ArrayField(models.CharField(max_length=250), blank=True, null=True)  # Array of attribute value /without headers

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="cocept_code_attr_created")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="cocept_code_attr_modified")
    
    history = HistoricalRecords()


    class Meta:
        ordering = ('created',)

    def __str__(self):
        return self.code
