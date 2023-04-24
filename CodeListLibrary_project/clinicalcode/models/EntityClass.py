from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

from clinicalcode.constants import *

class EntityClass(models.Model):
    '''
        EntityClass
            Describes the entity class of a template incl. its prefix
    '''

    ''' Metadata '''
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    entity_prefix = models.CharField(editable=True, max_length=4)
    entity_count = models.BigIntegerField(default=0, null=False, editable=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, default=None, related_name="entity_class_creator")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, default=None, related_name="entity_class_updater")
    created = models.DateTimeField(default=now, editable=False)
    modified = models.DateTimeField(default=now, editable=False)
    
    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
