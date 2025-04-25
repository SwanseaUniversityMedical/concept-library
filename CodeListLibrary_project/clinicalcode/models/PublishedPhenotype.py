from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

from .Phenotype import Phenotype

User = get_user_model()

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
    )

    approval_status = models.IntegerField(default=0)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = (("phenotype", "phenotype_history_id"), )
