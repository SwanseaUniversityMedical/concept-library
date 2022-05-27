from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

from .Phenotype import Phenotype


class PublishedPhenotype(models.Model):
    phenotype = models.ForeignKey(Phenotype, on_delete=models.CASCADE)
    phenotype_history_id = models.IntegerField(null=False)
    created = models.DateTimeField(auto_now_add=True)  # date of publication
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="ph_publication_owner")
    modified = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="published_phenotype_modified"
    )  # user of the person who modified this row.

    approval_status = models.IntegerField(default=0)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = (("phenotype", "phenotype_history_id"), )
