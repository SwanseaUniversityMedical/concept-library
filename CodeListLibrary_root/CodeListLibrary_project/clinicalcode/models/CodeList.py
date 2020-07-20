from django.contrib.auth.models import User
from django.db import models
from .Component import Component
from simple_history.models import HistoricalRecords
from .TimeStampedModel import TimeStampedModel


class CodeList(TimeStampedModel):

    # Type of codes in the code list
    component = models.OneToOneField(Component,
                                     on_delete=models.CASCADE,
                                     blank=True,
                                     null=True)

    description = models.CharField(max_length=250)
    sql_rules = models.CharField(max_length=1000, blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)
