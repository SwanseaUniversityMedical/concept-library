from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

from .GenericEntity import GenericEntity


class PublishedGenericEntity(models.Model):
    entity = models.ForeignKey(GenericEntity, on_delete=models.CASCADE)
    entity_history_id = models.IntegerField(null=False)
    entity_prefix = models.CharField(null=True, max_length=4, editable=False)
    code_count = models.IntegerField(null=True) # used for statistics
    
    created = models.DateTimeField(auto_now_add=True)  # date of publication
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="published_entity_created_by")
    modified = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.ForeignKey(User,
                                    on_delete=models.SET_NULL,
                                    null=True,
                                    related_name="published_entity_modified_by"
                                )  # user of the person who modified this row.

    approval_status = models.IntegerField(default=0)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = (("entity", "entity_history_id"), )
