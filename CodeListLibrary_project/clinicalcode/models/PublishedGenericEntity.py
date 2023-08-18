from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from django.db import connection, transaction

import enum

from .GenericEntity import GenericEntity
from ..entity_utils import constants

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
        '''
            update publish_status in historicalgenericentity
        '''
        if isinstance(self.approval_status, enum.Enum):
            self.approval_status = self.approval_status.value
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                sql_publish_status = """
                                        UPDATE public.clinicalcode_historicalgenericentity 
                                        SET publish_status = """ + str(self.approval_status) + """
                                        WHERE id = '""" + str(self.entity.id) + """'and history_id = """ + str(self.entity_history_id) + """ ;
                                    """
                
                cursor.execute(sql_publish_status)
                
            ''' if latest version, then update live record '''
            if self.entity_history_id == self.entity.history.latest().history_id:
                with connection.cursor() as cursor:
                    sql_publish_status_2 = """
                                        UPDATE public.clinicalcode_genericentity 
                                        SET publish_status = """ + str(self.approval_status) + """
                                        WHERE id = '"""+ str(self.entity.id)+"""' ;
                                    """
                    cursor.execute(sql_publish_status_2)                    

        super(PublishedGenericEntity, self).save(*args, **kwargs)
        
    class Meta:
        unique_together = (("entity", "entity_history_id"), )
