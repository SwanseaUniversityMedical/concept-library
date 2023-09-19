from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.db import models
from django.db import transaction
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from .Template import Template
from .EntityClass import EntityClass
from ..entity_utils import gen_utils, constants

class GenericEntityManager(models.Manager):
    '''
        Generic Entity Manager
            @desc responsible for transfering previous phenotype records to generic entities
                without using the incremental PK
    '''
    def transfer_record(self, *args, **kwargs):
        ignore_increment = kwargs.pop('ignore_increment', False)
        
        entity = self.model(**kwargs)
        entity.save(ignore_increment=ignore_increment)
        return entity

class GenericEntity(models.Model):
    """
        Generic Entity Model
    """
    objects = GenericEntityManager()

    id = models.CharField(primary_key=True, editable=False, max_length=50)

    ''' Common metadata '''
    name = models.CharField(max_length=250)
    status = models.IntegerField(choices=[(e.name, e.value) for e in constants.ENTITY_STATUS], default=constants.ENTITY_STATUS.DRAFT)
    author = models.CharField(max_length=1000)
    definition = models.TextField(null=True, blank=True)
    implementation = models.TextField(null=True, blank=True)
    validation = models.TextField(null=True, blank=True)
    publications = JSONField(blank=True, null=True)
    tags = ArrayField(models.IntegerField(), blank=True, null=True)
    collections = ArrayField(models.IntegerField(), blank=True, null=True)
    citation_requirements = models.TextField(null=True, blank=True)
    brands = ArrayField(models.IntegerField(), blank=True, null=True)
    
    ''' Search vector fields '''
    search_vector = SearchVectorField(null=True)

    ''' Model templating '''
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, related_name="entity_template")
    template_data = JSONField(blank=True, null=True)
    template_version = models.IntegerField(null=True, editable=False)

    ''' Creation information '''
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_updated")
    is_deleted = models.BooleanField(null=True, default=False)
    
    ''' Subject to change '''
    internal_comments = models.TextField(null=True, blank=True) # e.g. archive reasons, not to be shown elsewhere

    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="entity_deleted")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="entity_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)

    owner_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.OWNER_PERMISSIONS], default=constants.OWNER_PERMISSIONS.EDIT)
    group_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.GROUP_PERMISSIONS], default=constants.GROUP_PERMISSIONS.NONE)
    world_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.WORLD_ACCESS_PERMISSIONS], default=constants.WORLD_ACCESS_PERMISSIONS.NONE)
    
    ''' Publish status '''
    publish_status = models.IntegerField(null=True, choices=[(e.name, e.value) for e in constants.APPROVAL_STATUS], default=constants.APPROVAL_STATUS.ANY)

    ''' Historical data '''
    history = HistoricalRecords()

    def save(self, ignore_increment=False, *args, **kwargs):
        '''
            [!] Note:
                1. On creation, increments counter within template and increment's entity ID by count + 1
                
                2. template_version field is computed from the template_data.version field
        '''
        template_layout = self.template
        if template_layout is not None:
            entity_class = getattr(template_layout, 'entity_class')
            if entity_class is not None:
                if ignore_increment:
                    with transaction.atomic():
                        entitycls = EntityClass.objects.select_for_update().get(pk=entity_class.id)
                        entity_id = gen_utils.parse_int(
                            self.id.replace(entitycls.entity_prefix, ''), 
                            default=None
                        )

                        if not entity_id: 
                            raise ValidationError('Unable to parse entity id')

                        if entitycls.entity_count < entity_id:
                            entitycls.entity_count = entity_id
                            entitycls.save()
                elif not self.pk and not ignore_increment:
                    with transaction.atomic():
                        entitycls = EntityClass.objects.select_for_update().get(pk=entity_class.id)
                        index = entitycls.entity_count = entitycls.entity_count + 1
                        self.id = f'{entitycls.entity_prefix}{index}'
                        entitycls.save()

        if self.template_data and 'version' in self.template_data:
            self.template_version = self.template_data.get('version')

        super(GenericEntity, self).save(*args, **kwargs)

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

    class Meta:
        indexes = [
            GinIndex(fields=['search_vector']),
            GinIndex(
                name='ge_id_ln_gin_idx',
                fields=['id'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='ge_name_ln_gin_idx',
                fields=['name'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='ge_definition_ln_gin_idx',
                fields=['definition'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='ge_author_ln_gin_idx',
                fields=['author'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='ge_impl_ln_gin_idx',
                fields=['implementation'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='ge_val_ln_gin_idx',
                fields=['validation'],
                opclasses=['gin_trgm_ops']
            )
        ]
        ordering = ('name', )

    def __str__(self):
        return self.name
