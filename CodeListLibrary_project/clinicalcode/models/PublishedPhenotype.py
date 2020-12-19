from django.contrib.auth.models import User
from django.db import models
from .Phenotype import  Phenotype


class PublishedPhenotype(models.Model):
    phenotype = models.ForeignKey(Phenotype)
    phenotype_history_id = models.IntegerField(null=False)
    created = models.DateTimeField(auto_now_add=True)  # date of creation
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="ph_publication_owner")
    
    class Meta:
        unique_together = (("phenotype", "phenotype_history_id"),)
