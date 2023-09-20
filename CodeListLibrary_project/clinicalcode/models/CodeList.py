from django.db import models
from simple_history.models import HistoricalRecords

from .Component import Component
from .TimeStampedModel import TimeStampedModel


class CodeList(TimeStampedModel):
    component = models.OneToOneField(Component,
                                     on_delete=models.CASCADE,
                                     blank=True,
                                     null=True)

    description = models.CharField(max_length=1000)
    sql_rules = models.CharField(max_length=1000, blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)
