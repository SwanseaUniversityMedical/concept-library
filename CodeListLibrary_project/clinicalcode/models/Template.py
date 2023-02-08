from django.contrib.auth.models import Group, User
#from django.contrib.postgres.fields import JSONField
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.postgres.fields import ArrayField

from .TimeStampedModel import TimeStampedModel
from .Brand import Brand
from clinicalcode.constants import *

class Template(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    layout = models.IntegerField(choices=ENTITY_LAYOUT) # clinical_phenotype / NLP_phenotype / workingset, ....
    description = models.TextField(blank=True, null=True)
    
    definition = JSONField(blank=True, null=True)

    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name="template_brand")
    
    # take most recent
    #is_default = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="template_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="template_updated")
    
    
    history = HistoricalRecords()

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
