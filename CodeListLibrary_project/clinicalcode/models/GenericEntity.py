from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError

from .TimeStampedModel import TimeStampedModel
from .Template import Template
from clinicalcode.constants import *
from django.db import transaction

'''
    Generic Entity Manager
        @desc responsible for transfering previous phenotype records to generic entities
              without using the incremental PK
'''
class GenericEntityManager(models.Manager):
    def transfer_record(self, *args, **kwargs):
        ignore_increment = kwargs.pop('ignore_increment', False)
        
        entity = self.model(**kwargs)
        entity.save(ignore_increment=ignore_increment)
        return entity

"""
    Generic Entity Model
"""
class GenericEntity(models.Model):
    objects = GenericEntityManager()

    id = models.AutoField(primary_key=True)
    
    ''' Entity ID '''
    entity_prefix = models.CharField(null=True, max_length=4, editable=False)
    entity_id = models.IntegerField(unique=False, null=True, editable=False) # unique for every class, but non-unique across classes

    ''' Common metdata '''
    name = models.CharField(max_length=250)
    status = models.IntegerField(choices=ENTITY_STATUS, default=ENTITY_STATUS_DRAFT)
    author = models.CharField(max_length=1000)
    definition = models.TextField(null=True, blank=True)
    implementation = models.TextField(null=True, blank=True)
    validation = models.TextField(null=True, blank=True)
    publications = ArrayField(models.CharField(max_length=500), blank=True, null=True)
    tags = ArrayField(models.IntegerField(), blank=True, null=True) 
    collections = ArrayField(models.IntegerField(), blank=True, null=True)   
    citation_requirements = models.TextField(null=True, blank=True)  # Any request for citation requirements to be honoured

    ''' Model templating '''
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, related_name="entity_template")
    template_data = JSONField(blank=True, null=True)

    ''' Creation information '''
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_updated")
    is_deleted = models.BooleanField(null=True, default=False)
    
    ''' Subject to change '''
    internal_comments = models.TextField(null=True, blank=True) # for create/update forms only, not to be shown elsewhere

    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="entity_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)

    owner_access = models.IntegerField(choices=PERMISSION_CHOICES, default=EDIT)
    group_access = models.IntegerField(choices=PERMISSION_CHOICES, default=NONE)
    world_access = models.IntegerField(choices=PERMISSION_CHOICES, default=NONE)

    ''' Historical data '''
    history = HistoricalRecords()

    '''
        On creation, increments counter within template and increment's entity ID by count + 1
        Otherwise, update model and the template statistics based on our new data
    '''
    def save(self, ignore_increment=False, *args, **kwargs):
        # Update 
        if self.pk is None:
            template_layout = self.template
            if template_layout is not None:
                with transaction.atomic():
                    template = Template.objects.select_for_update().get(pk=template_layout.id)
                    if not ignore_increment:
                        index = template.entity_count = template.entity_count + 1
                        self.entity_id = index
                        self.entity_prefix = template_layout.entity_prefix
                        template.save()
                    else:
                        if template.entity_count < self.entity_id:
                            template.entity_count = self.entity_id
                            template.save()
        
        # Update statistics
        

        super(GenericEntity, self).save(*args, **kwargs)

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
    
    
