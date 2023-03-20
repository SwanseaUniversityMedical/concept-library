from django.db import models
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField

class ConceptReviewStatus(models.Model):
    id = models.AutoField(primary_key=True)
    concept_id = models.IntegerField(null=True, blank=True)
    history_id = models.IntegerField(null=True, blank=True)

    review_submitted = models.BooleanField(null=True, default=False)
    last_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviewed_concepts')
    
    comment = models.TextField(null=True, blank=True)

    '''
        Once we move to V2 we need to modify this struct.
        
        Instead of ArrayFields, we need to utilise ManyToMany fields
        to reduce complexity & computational time
    '''
    included_codes = ArrayField(models.IntegerField(), blank=True, null=True)
    excluded_codes = ArrayField(models.IntegerField(), blank=True, null=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return self.name
