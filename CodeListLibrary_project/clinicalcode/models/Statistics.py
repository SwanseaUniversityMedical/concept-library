from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

from clinicalcode.models.TimeStampedModel import TimeStampedModel

User = get_user_model()

class Statistics(TimeStampedModel):
    org = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    stat = JSONField()
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="stat_created")
    updated_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="stat_updated")

    history = HistoricalRecords()

    class Meta:
        ordering = ('org', )

    def __str__(self):
        return self.org
