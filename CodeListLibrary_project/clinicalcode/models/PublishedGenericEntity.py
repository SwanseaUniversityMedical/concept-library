from django.db import models
from simple_history.models import HistoricalRecords
from django.db import connection, transaction
from django.contrib.auth import get_user_model

import enum

from .GenericEntity import GenericEntity
from ..entity_utils import constants

User = get_user_model()

class PublishedGenericEntity(models.Model):
    entity = models.ForeignKey(GenericEntity, on_delete=models.CASCADE)
    entity_history_id = models.IntegerField(null=False)
    code_count = models.IntegerField(null=True) # used for statistics

    created = models.DateTimeField(auto_now_add=True)  # date of publication
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="published_entity_created_by")
    modified = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="published_entity_modified_by")  # user of the person who modified this row.

    approval_status = models.IntegerField(choices=[(e.name, e.value) for e in constants.APPROVAL_STATUS], default=constants.APPROVAL_STATUS.REQUESTED)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        """
            Update publish_status in historicalgenericentity
        """
        if isinstance(self.approval_status, enum.Enum):
            self.approval_status = self.approval_status.value
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                sql = '''
                do $tx$
                declare
                    v_latest bigint;
                begin
                    update public.clinicalcode_historicalgenericentity
                       set publish_status = %(approval)s
                     where id = %(entityid)s
                       and history_id = %(entityhxid)s;

                    select max(history_id)
                      into v_latest
                      from public.clinicalcode_historicalgenericentity
                     where id = %(entityid)s;

                    if (v_latest = %(entityhxid)s) then
                        update public.clinicalcode_genericentity
                           set publish_status = %(approval)s
                         where id = %(entityid)s;
                    end if;
                end;
                $tx$ language plpgsql;
                '''
                cursor.execute(sql, params={
                    'approval': self.approval_status,
                    'entityid': str(self.entity.id),
                    'entityhxid': self.entity_history_id,
                })

        super(PublishedGenericEntity, self).save(*args, **kwargs)
        
    class Meta:
        unique_together = (("entity", "entity_history_id"), )
