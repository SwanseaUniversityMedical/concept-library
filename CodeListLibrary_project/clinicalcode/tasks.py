from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.test.client import RequestFactory
from django.core import management

import time

from clinicalcode.entity_utils import stats_utils, email_utils

@shared_task(bind=True)
def send_message_test(self):
    return 'test message'

@shared_task(name="review_email_background_task")
def send_review_email(request,data):
    email_utils.send_review_email_generic(request, data)
    return f"Email sent - {data['id']} with name {data['entity_name']} and owner_id {data['entity_user_id']}"

@shared_task(bind=True)
def send_scheduled_email(self):
    email_subject = 'Phenotypes: Weekly Email'
    email_content = email_utils.get_scheduled_email_to_send()

    owner_ids = list(set([c['owner_id'] for c in email_content]))
    owner_email = list(set([c['owner_email'] for c in email_content]))
    overal_result = []
    for i in range(len(owner_ids)):
        overal_result.append({'owner_id': owner_ids[i], 
                              'owner_email': owner_email[i], 
                              'content': ''.join(
                                                [str(email_content[n]['email_content']) for n in range(len(email_content)) if
                                                 email_content[n]['owner_id'] == owner_ids[i]])
                              })

    for j in range(len(overal_result)):
        if not settings.IS_DEVELOPMENT_PC or settings.HAS_MAILHOG_SERVICE:
            try:
                time.sleep(7)
                msg = EmailMultiAlternatives(email_subject,
                                             overal_result[j]['content'],
                                             'Helpdesk <%s>' % settings.DEFAULT_FROM_EMAIL,
                                             to=[overal_result[j]['owner_email']]
                                             )
                msg.content_subtype = 'html'
                msg.send()
            except BadHeaderError:
                return False
    return True, overal_result

@shared_task(bind=True)
def run_daily_statistics(self):
    '''
        Daily cronjob to update statistics for entities
    '''
    logger = get_task_logger('cll')
    try:
        stats_utils.collect_statistics(None)

        request = RequestFactory().get('/')
        request.user = stats_utils.MockStatsUser()
        # setattr(request, 'CURRENT_BRAND', )
        stats_utils.save_homepage_stats(request, is_mock=True)
    except Exception as e:
        logger.warning(f'Unable to run daily statistics job, got error {e}')
        return False
    else:
        logger.info(f'Successfully updated statistics')
        return True

@shared_task(bind=True)
def run_weekly_cleanup(self):
    '''
        Runs the clear_session.py management command
    '''
    management.call_command('clear_sessions')
    return True
