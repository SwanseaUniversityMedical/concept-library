from datetime import datetime
from django.db import models, transaction
from django.utils.timezone import now, make_aware
from django.contrib.auth.models import Group, User

from .DeltaMixin import DeltaModelMixin
from ..entity_utils import constants
from ..managers.HistoricalManager import CurrentRecordManager, HistoricalRecordManager, HistoricalQuerySet

class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(self, owner_cls, owner_self)

class HistoricalModelMixin(models.Model, DeltaModelMixin):
    id = models.AutoField(primary_key=True)
    entity_id = models.BigIntegerField(db_index=True, editable=False)
    version_id = models.BigIntegerField(db_index=True, editable=False, default=1)
    version_date = models.DateTimeField(db_index=True, editable=False, default=now, blank=True)
    created_date = models.DateTimeField(db_index=True, editable=False, default=now, blank=True)
    change_reason = models.TextField(null=True, blank=True)
    change_type = models.IntegerField(choices=[(e.name, e.value) for e in constants.HISTORICAL_CHANGE_TYPE], default=constants.HISTORICAL_CHANGE_TYPE.CREATED)

    objects = CurrentRecordManager()

    ''' Meta '''
    class Meta:
        abstract = True

    ''' Properties '''    
    @property
    def is_historic(self):
        if self.pk is None:
            return
        return self.history.most_recent().pk != self.pk

    @classproperty
    def history(self, model, instance):
        queryset = HistoricalRecordManager.from_queryset(HistoricalQuerySet)
        return queryset(model, instance)
    
    ''' Model Methods '''
    def __init__(self, *args, **kwargs):
        super(HistoricalModelMixin, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk is None:
            return self.__create_new_record(*args, **kwargs)
        return self.__create_new_version(*args, **kwargs)

    ''' Private Methods '''
    def __get_next_id(self):
        last = self._meta.model.objects.order_by('-id').first()
        if last is not None:
            return last.id + 1
        return 1

    def __create_new_record(self, *args, **kwargs):
        with transaction.atomic():
            self.entity_id = self.entity_id or self.__get_next_id()
            self.change_reason = 'CREATED'
            self.change_type = constants.HISTORICAL_CHANGE_TYPE.CREATED
            super(HistoricalModelMixin, self).save(*args, **kwargs)
        return self
    
    def __create_new_version(self, *args, **kwargs):
        with transaction.atomic():
            last_version = self.history.most_recent()

            self.pk = None
            self.version_id = last_version.version_id + 1
            self.version_date = make_aware(datetime.now())
            self.created_date = last_version.created_date
            self.change_reason = 'UPDATED'
            self.change_type = constants.HISTORICAL_CHANGE_TYPE.EDITED
            super(HistoricalModelMixin, self).save(*args, **kwargs)

        return self
