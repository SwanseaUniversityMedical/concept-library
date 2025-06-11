from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

from .PhenotypeWorkingset import PhenotypeWorkingset

User = get_user_model()

class PublishedWorkingset(models.Model):
    workingset = models.ForeignKey(PhenotypeWorkingset, on_delete=models.CASCADE)
    workingset_history_id = models.IntegerField(null=False)
    created = models.DateTimeField(auto_now_add=True)  # date of publication
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="workingset_owner")
    modified = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="workingset_modified")
    approval_status = models.IntegerField(default=0)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    history = HistoricalRecords()

    class Meta:
        unique_together = (("workingset", "workingset_history_id") )