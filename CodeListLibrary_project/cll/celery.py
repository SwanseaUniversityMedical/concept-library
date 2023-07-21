from __future__ import absolute_import

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cll.settings')
app = Celery('cll')
app.config_from_object('django.conf:settings', namespace='CELERY')
# Load tasks from all registered apps

schedule = {
    # Publication & Update emails
    'send_mail': {
        'task': 'clinicalcode.tasks.send_scheduled_email',
        'schedule': crontab(minute=0,hour='9,18')
    },

    # Sync sources
    'celery_run_data_sync':{
        'task': 'clinicalcode.views.Admin.run_celery_datasource',
        'schedule': crontab(minute=0, hour='9,18')
    },

    # Statistics job
    'celery_run_stats': {
        'task': 'clinicalcode.tasks.run_daily_statistics',
        'schedule': crontab(minute=0, hour=0)
    },

    # Session cleanup task
    'celery_run_cleanup': {
        'task': 'clinicalcode.tasks.run_weekly_cleanup',
        'schedule': crontab(hour=0, minute=0, day_of_week='sunday'),
    },
}

# Any current debug tasks
if settings.DEBUG:
    schedule |= {
        'send_message_test': {
            'task': 'clinicalcode.tasks.send_message_test',
            'schedule': crontab(minute=0,hour='9,18')
        },
    }

    @app.task(bind=True)
    def debug_task(self):
        print(f'Request: {self.request!r}')

app.conf.beat_schedule = schedule
app.autodiscover_tasks()
