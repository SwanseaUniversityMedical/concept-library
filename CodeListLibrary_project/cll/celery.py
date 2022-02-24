from __future__ import absolute_import

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cll.settings')
app = Celery('cll')
app.config_from_object('django.conf:settings', namespace='CELERY')
# Load tasks from all registered apps

app.conf.beat_schedule = {
    'send_mail': {
        'task': 'clinicalcode.tasks.send_scheduled_email',
        'schedule': crontab(minute=60)
    },
    'send_message_test': {
        'task': 'clinicalcode.tasks.send_message_test',
        'schedule': crontab(minute=60)
    }

}

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
