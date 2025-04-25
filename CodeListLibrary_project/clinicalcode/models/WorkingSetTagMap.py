from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

from .Tag import Tag
from .WorkingSet import WorkingSet
from .TimeStampedModel import TimeStampedModel

User = get_user_model()

class WorkingSetTagMap(TimeStampedModel):
    workingset = models.ForeignKey(WorkingSet, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="workingsettagmaps_created")

    history = HistoricalRecords()
