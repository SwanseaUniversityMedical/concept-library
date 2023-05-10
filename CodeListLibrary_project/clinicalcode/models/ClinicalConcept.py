from django.db import models
from django.contrib.postgres.fields import ArrayField

from .Code import Code
from .CodingSystem import CodingSystem
from .GenericEntity import GenericEntity
from ..mixins.HistoricalMixin import HistoricalModelMixin
from ..entity_utils import constants

class ClinicalRuleset(models.Model):
    '''
    
    '''
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    source_type = models.IntegerField(choices=[(e.name, e.value) for e in constants.CLINICAL_CODE_SOURCE], default=constants.CLINICAL_CODE_SOURCE.SEARCH_TERM)
    logical_type = models.IntegerField(choices=[(e.name, e.value) for e in constants.CLINICAL_RULE_TYPE], default=constants.CLINICAL_RULE_TYPE.INCLUDE)
    codes = models.ManyToManyField(Code, blank=True, related_name='rulesets', through='ClinicalCodeItem')

    ''' Meta '''
    class Meta:
        ordering = ('name', )
    
    ''' Properties '''
    @property
    def code_count(self):
        '''
        '''
        return 0

    @property
    def codelist(self):
        '''
        
        '''
        return None

    ''' Methods '''

    ''' Operators '''
    def __str__(self):
        return self.name

class ClinicalCodeItem(models.Model):
    '''
    
    '''
    ruleset = models.ForeignKey(ClinicalRuleset, on_delete=models.CASCADE)
    code = models.ForeignKey(Code, on_delete=models.CASCADE)
    attributes = ArrayField(models.CharField(max_length=250), blank=True, null=True)

class ClinicalConcept(HistoricalModelMixin):
    '''
    
    '''

    ''' Data '''
    # Metadata
    name = models.CharField(max_length=250)

    # Forking
    root_concept = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='forked_concepts')

    # Phenotype parent
    parent = models.ForeignKey(GenericEntity, on_delete=models.CASCADE, null=True, blank=True, related_name='child_concepts')

    # Clinical data
    rulesets = models.ManyToManyField(ClinicalRuleset, blank=True, related_name='parent_concepts')
    coding_system = models.ForeignKey(CodingSystem, on_delete=models.SET_NULL, null=True, blank=True, related_name='coded_concepts')
    code_attribute_header = ArrayField(models.CharField(max_length=100), blank=True, null=True)

    ''' Meta '''
    class Meta:
        ordering = ('name', )

    def save(self, *args, **kwargs):
        super(ClinicalConcept, self).save(*args, **kwargs)

    ''' Properties '''
    @property
    def code_count(self):
        '''
        '''
        return 0

    @property
    def codelist(self):
        '''
            Property to return aggregated codes from codelists of each ruleset

            e.g. 
                concept = ClinicalConcept.objects.all().first()
                codelist = concept.codelist
        '''
        return None

    ''' Methods '''
    def can_edit(self, user):
        '''
            Det. whether the user is able to edit this Concept based on its parent's permissions

            e.g. 
                user = request.user
                concept = ClinicalConcept.objects.all().first()

                if concept.can_user_edit(user):
                    print('Do things')
        '''
        return True

    ''' Operators '''
    def __str__(self):
        return self.name

class LegacyClinicalData(models.Model):
    '''
    
    '''
    id = models.AutoField(primary_key=True)
    parent = models.ForeignKey(ClinicalConcept, on_delete=models.CASCADE, null=True, blank=True, related_name='legacy_details')
    
    entry_date = models.DateField()
    author = models.CharField(max_length=1000)
    description = models.TextField(null=True, blank=True)
    tags = ArrayField(models.IntegerField(), blank=True, null=True)
    collections = ArrayField(models.IntegerField(), blank=True, null=True)
    validation_performed = models.BooleanField(null=True, default=False)
    validation_description = models.TextField(null=True, blank=True)
    publication_doi = models.CharField(max_length=100)
    publication_link = models.URLField(max_length=1000)
    secondary_publication_links = models.TextField(null=True, blank=True)
    paper_published = models.BooleanField(null=True, default=False)
    source_reference = models.CharField(max_length=250)
    citation_requirements = models.TextField(null=True, blank=True)
