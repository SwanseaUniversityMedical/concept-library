'''
    TimeStampedModel

    The abstract base class for all CLL models.
    Adds created and modified time-stamps for each instance.
'''
from django.db import models


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now_add=True)  #, null=True, blank=True)

    class Meta:
        abstract = True
