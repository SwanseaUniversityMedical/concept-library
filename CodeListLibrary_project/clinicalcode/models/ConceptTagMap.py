from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from clinicalcode.models.TimeStampedModel import TimeStampedModel
from .Concept import Concept
from .Tag import Tag


class ConceptTagMap(TimeStampedModel):
    concept = models.ForeignKey(Concept)
    tag = models.ForeignKey(Tag)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="concepttagmaps_created")

    history = HistoricalRecords()
