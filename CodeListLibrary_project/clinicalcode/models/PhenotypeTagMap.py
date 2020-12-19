from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from clinicalcode.models.TimeStampedModel import TimeStampedModel
from .Phenotype import Phenotype
from .Tag import Tag


class PhenotypeTagMap(TimeStampedModel):
    phenotype = models.ForeignKey(Phenotype)
    tag = models.ForeignKey(Tag)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="phenotypetagmaps_created")

    history = HistoricalRecords()
