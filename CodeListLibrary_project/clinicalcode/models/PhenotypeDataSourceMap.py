from clinicalcode.models.TimeStampedModel import TimeStampedModel
from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

from .DataSource import DataSource
from .Phenotype import Phenotype


class PhenotypeDataSourceMap(TimeStampedModel):
    phenotype = models.ForeignKey(Phenotype, on_delete=models.CASCADE)
    datasource = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="phenotypedatasourcemaps_created")

    history = HistoricalRecords()
