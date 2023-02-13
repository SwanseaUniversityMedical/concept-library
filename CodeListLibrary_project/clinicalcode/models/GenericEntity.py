from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords

# from ..permissions import Permissions
# from .DataSource import DataSource
from .TimeStampedModel import TimeStampedModel
from .Template import Template
from clinicalcode.constants import *

class GenericEntity(models.Model):
    """
        Generic Entity Model
    """
    serial_id = models.IntegerField()
    
    id = models.CharField(primary_key=True, editable=True, max_length=50)

    name = models.CharField(max_length=250)
    author = models.CharField(max_length=1000) # Think about author-list
    
    layout = models.IntegerField(choices=ENTITY_LAYOUT) # clinical_phenotype / NLP_phenotype / workingset, ....
    status = models.IntegerField(choices=ENTITY_STATUS, 
                                default=ENTITY_STATUS_DRAFT)
    
    # move to template
    #type = models.CharField(max_length=50) # sub-type like in clinical_phenotype(Drug/Biomarker, ...) NEED TO ENUM
            
    tags = ArrayField(models.IntegerField(), blank=True, null=True) 
    # link brand
    collections = ArrayField(models.IntegerField(), blank=True, null=True)   
    
    description = models.TextField(null=True, blank=True)
    implementation = models.TextField(null=True, blank=True)
    validation = models.TextField(null=True, blank=True)
    publications = ArrayField(models.CharField(max_length=500), blank=True, null=True)
    citation_requirements = models.TextField(null=True, blank=True)  # Any request for citation requirements to be honoured


    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, related_name="entity_template")
    template_data = JSONField(blank=True, null=True)
    template_data2 = JSONField(blank=True, null=True)

    #brands = ArrayField(models.IntegerField(), blank=True, null=True)
    
    # managed by app
    internal_comments = models.TextField(null=True, blank=True) # for create/update forms only, not to be shown elsewhere
        
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_updated")
    is_deleted = models.BooleanField(null=True, default=False)

    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)

    owner_access = models.IntegerField(choices=PERMISSION_CHOICES, default=EDIT)
    group_access = models.IntegerField(choices=PERMISSION_CHOICES, default=NONE)
    world_access = models.IntegerField(choices=PERMISSION_CHOICES, default=NONE)


    history = HistoricalRecords()


    def save(self,  *args, **kwargs):
        # This means that the model isn't saved to the database yet
        
        # if create new, then calculate new ids
        if (not self.id):            
            count_all = GenericEntity.objects.count()
            if count_all:
                count_all += 1
            else:
                count_all = 1
            # serial auto-increment field
            self.serial_id = count_all
            
            #if  (not self.id) or (override_id):   
            count = None                
            prefix = ''
    
            entity = 'phenotype' # for now
            entity = entity.lower()
            # count only same entity
            count = GenericEntity.objects.filter(layout__in = [t[0]  for t in ENTITY_LAYOUT if t[1].lower().replace(' ', '').find(entity) != -1] ).count()
            if entity == 'phenotype':
                prefix = 'PH'
            elif entity == 'concept':
                prefix = 'C'
            elif entity == 'workingset':
                prefix = 'WS'
                
                
            if count:
                count += 1   
            else:
                count = 1                   
            self.id = prefix + str(count)

        super(GenericEntity, self).save(*args, **kwargs)            


    def save_migrate_phenotypes(self, *args, **kwargs):
        # This means that the model isn't saved to the database yet
        
        entity = 'phenotype'
        serial_id = False
        override_id = False
        
        # if create new, then calculate new ids
        #if (not self.id) or (serial_id):            
        count_all = GenericEntity.objects.count()
        if count_all:
            count_all += 1
        else:
            count_all = 1
        # serial auto-increment field
        #self.serial_id = count_all
            
        # #if  (not self.id) or (override_id):   
        # count = None                
        # prefix = ''
        #
        # entity = entity.lower()
        # # count only same entity
        # count = GenericEntity.objects.filter(layout__in = [t[0]  for t in ENTITY_LAYOUT if t[1].lower().replace(' ', '').find(entity) != -1] ).count()
        # if entity == 'phenotype':
        #     prefix = 'PH'
        # elif entity == 'concept':
        #     prefix = 'C'
        # elif entity == 'workingset':
        #     prefix = 'WS'
        #
        #
        # if count:
        #     count += 1   
        # else:
        #     count = 1                   
        # #self.id = prefix + str(count)

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
    
    
