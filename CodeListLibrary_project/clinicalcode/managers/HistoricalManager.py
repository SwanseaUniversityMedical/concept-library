from django.db import models
from django.db.models import QuerySet

from ..entity_utils import constants

class HistoricalQuerySet(QuerySet):
    '''
        Replicate QuerySet behaviour of historical records

        e.g.
            ClinicalConcept.history.get(entity_id__in=[1, 2]).latest_of_each()
        
    '''
    def filter(self, *args, **kwargs):
        return super().filter(*args, **kwargs)
    
    def latest_of_each(self):
        latest_versions = self.order_by('-entity_id', '-version_date') \
                                .distinct('entity_id') \
                                .values_list('pk', flat=True)
        return self.filter(pk__in=latest_versions)

class CurrentRecordManager(models.Manager):    
    def get_super_queryset(self):
        queryset = super().get_queryset()
        latest_live_versions = queryset.exclude(change_reason=constants.HISTORICAL_CHANGE_TYPE.DELETED.value) \
                                .order_by('-entity_id', '-version_date') \
                                .distinct('entity_id') \
                                .values_list('pk', flat=True)
        return queryset.filter(pk__in=latest_live_versions)

    def get_queryset(self):
        return self.get_super_queryset()

class HistoricalRecordManager(models.Manager):
    '''
        Replicate class level behaviour of historical records

        e.g.
            ClinicalConcept.history.all()
    '''
    def __init__(self, model, instance=None):
        super().__init__()
        self.model = model
        self.instance = instance
    
    def get_super_queryset(self):
        return super().get_queryset()

    def get_queryset(self):
        if self.instance is None:
            return self.get_super_queryset()
        return self.get_super_queryset().filter(entity_id=self.instance.entity_id)

    def most_recent(self):
        if not self.instance:
            return
        return self.get_queryset().order_by('-version_date').first()

    def earliest(self):
        if not self.instance:
            return
        return self.get_queryset().order_by('version_date').first()
