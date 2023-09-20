from __future__ import absolute_import
from celery import Celery
from django.conf import settings

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cll.settings')
app = Celery('cll')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from all registered apps
"""
    Use schedule only for specific tasks that need to be forced to run at a specific time

    Example:

        schedule = {
            # Publication & Update emails
            'send_mail': {
                'task': 'clinicalcode.tasks.send_scheduled_email',
                'schedule': crontab(minute=0,hour='9,18')
            },
        }

"""

# Any current debug tasks
if settings.DEBUG:
    @app.task(bind=True)
    def debug_task(self):
        print(f'Request: {self.request!r}')

# In order to register task in the Celery beat
# app.conf.beat_schedule = schedule 
app.autodiscover_tasks()
