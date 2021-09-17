from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from .Concept import Concept


class PublishedConcept(models.Model):
    concept = models.ForeignKey(Concept)
    concept_history_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)  # date of publication
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="publication_owner")
    code_count = models.IntegerField(null=True)
    modified = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="published_concept_modified") # user of the person who modified this row.

    history = HistoricalRecords()
    
    class Meta:
        unique_together = (("concept", "concept_history_id"),)
