
from celery import shared_task
from celery import Celery
import os
# We can have either registered task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

#@shared_task(bind=True)
#def send_notifiction(self):
   #  print('test')
