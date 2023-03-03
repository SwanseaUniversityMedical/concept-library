from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError

# from ..permissions import Permissions
# from .DataSource import DataSource
from .TimeStampedModel import TimeStampedModel
from .Template import Template
from clinicalcode.constants import *
from django.db import transaction

@transaction.atomic
def increment_entity_count(id):
    try:
        template = Template.objects.select_for_update().get(pk=id)
        index = template.entity_count = template.entity_count + 1
        print(index)
        template.save()
        return index
    except Template.DoesNotExist:
        return -1

class GenericEntity(models.Model):
    """
        Generic Entity Model
    """
    id = models.AutoField(primary_key=True)
    
    ''' Entity ID '''
    entity_prefix = models.CharField(null=True, max_length=4, editable=False)
    entity_id = models.IntegerField(unique=True, null=True, editable=False)

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

    def save(self,  *args, **kwargs):
        ''' On creation, increments counter within template and increment's entity ID by count + 1 '''
        if self.pk is None:
            template_layout = self.template
            if template_layout is not None:
                index = increment_entity_count(template_layout.id)
                if index < 0:
                    raise ValidationError('Template layout does not exist')

                self.entity_id = index
                self.entity_prefix = template_layout.entity_prefix

        ''' Otherwise, update model and the template statistics based on our new data '''
        

        super(GenericEntity, self).save(*args, **kwargs)            


    '''
        Note to self:
            - Will need to change this + the admin command to account for changes to model
    '''
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
    
    
