from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

from .Tag import Tag
from .WorkingSet import WorkingSet
from .TimeStampedModel import TimeStampedModel

class WorkingSetTagMap(TimeStampedModel):
    workingset = models.ForeignKey(WorkingSet, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="workingsettagmaps_created")

    history = HistoricalRecords()
