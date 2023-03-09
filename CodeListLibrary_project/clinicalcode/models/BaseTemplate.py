from django.contrib.auth.models import User
from django.db.models import JSONField
from django.db import models

from .TimeStampedModel import TimeStampedModel
from clinicalcode.constants import *

class BaseTemplate(TimeStampedModel):
    ''' Metadata '''
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    definition = JSONField(blank=True, null=True, default=dict)

    ''' Instance data '''
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="basetemplate_created"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="basetemplate_updated"
    )

    def save(self,  *args, **kwargs):                  
        super(BaseTemplate, self).save(*args, **kwargs)
    
    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
