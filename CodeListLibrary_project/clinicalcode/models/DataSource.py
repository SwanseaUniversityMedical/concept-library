from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from clinicalcode.models.TimeStampedModel import TimeStampedModel

class DataSource(TimeStampedModel):
    """
        Data Source Model

        Representation of a Data Source imported from the HDR UK Gateway.
    """
    name = models.CharField(max_length=500)
    uid = models.CharField(max_length=250)
    url = models.CharField(max_length=500)
    description = models.CharField(max_length=500)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="data_source_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="data_source_updated")

    history = HistoricalRecords()

    def __str__(self):
        return self.name
