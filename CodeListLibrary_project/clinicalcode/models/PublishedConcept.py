
from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

from .Concept import Concept

User = get_user_model()

class PublishedConcept(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    concept_history_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)  # date of publication
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="publication_owner")
    code_count = models.IntegerField(null=True)
    modified = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="published_concept_modified"
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = (("concept", "concept_history_id"), )
