'''
    Working Set Model

    A working set is a list of columns from a number of Concepts.
'''
from django.contrib.auth.models import Group
from django.db.models import JSONField
from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

from .TimeStampedModel import TimeStampedModel
from ..entity_utils import constants

User = get_user_model()

class WorkingSet(TimeStampedModel):
    name = models.CharField(max_length=250)
    author = models.CharField(max_length=250)
    publication = models.CharField(max_length=3000)
    description = models.CharField(max_length=3000)
    concept_informations = JSONField()
    concept_version = JSONField(null=True)
    publication_doi = models.CharField(max_length=100)  # DOI of publication
    publication_link = models.URLField(max_length=1000)  # http link to pub
    secondary_publication_links = models.CharField(max_length=3000,
                                                   null=True,
                                                   blank=True)
    source_reference = models.CharField(max_length=250)  # Was this code list from another source?  Reference here.
    citation_requirements = models.CharField(max_length=250)  # Any request for citation requirements to be honoured

    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="working_set_created")
    updated_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="working_set_updated")
    is_deleted = models.BooleanField(null=True, default=False)
    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="working_set_deleted")
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,
                              null=True,
                              related_name="working_set_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    owner_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.OWNER_PERMISSIONS], default=constants.OWNER_PERMISSIONS.EDIT)
    group_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.GROUP_PERMISSIONS], default=constants.GROUP_PERMISSIONS.NONE)
    world_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.WORLD_ACCESS_PERMISSIONS], default=constants.WORLD_ACCESS_PERMISSIONS.NONE)

    friendly_id = models.CharField(max_length=50, default='', editable=False)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        self.friendly_id = 'WS' + str(self.id)
        super(WorkingSet, self).save(*args, **kwargs)

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
