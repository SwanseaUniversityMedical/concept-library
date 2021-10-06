from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from clinicalcode.models.TimeStampedModel import TimeStampedModel
from clinicalcode.models.Brand import Brand

class DataSource(TimeStampedModel):
    """
        Data Source Model

        Representation of a Data Source imported from the HDR UK Gateway.
    """
    name = models.CharField(max_length=500)
    uid = models.CharField(max_length=250, null=True, blank=True)
    url = models.CharField(max_length=500, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="data_source_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="data_source_updated")

    #brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="data_source_brand")


    history = HistoricalRecords()

    def __str__(self):
        return self.name

#     class Meta:
#         unique_together = (("name", "uid", "url", "description"),)