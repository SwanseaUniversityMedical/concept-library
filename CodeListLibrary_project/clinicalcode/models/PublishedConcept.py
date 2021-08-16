from django.contrib.auth.models import User
from django.db import models
from .Concept import Concept


class PublishedConcept(models.Model):
    concept = models.ForeignKey(Concept)
    concept_history_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)  # date of creation
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="publication_owner")
    code_count = models.IntegerField(null=True)
    
    class Meta:
        unique_together = (("concept", "concept_history_id"),)
