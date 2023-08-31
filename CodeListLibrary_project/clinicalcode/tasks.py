import time

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.core import management

from clinicalcode import db_utils
from clinicalcode.entity_utils import stats_utils

@shared_task(bind=True)
def send_message_test(self):
    return 'test message'

@shared_task(name="review_email_backgorund_task")
def send_review_email(request,data):
   # time.sleep(20)
    db_utils.send_review_email_generic(request,data)
    return f"Email sent - {data['id']} with name {data['entity_name']} and owner_id {data['owner_id']}"

@shared_task(bind=True)
def send_scheduled_email(self):
    email_subject = 'Weekly email Concept Library'
    email_content = db_utils.get_scheduled_email_to_send()

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
        if not settings.IS_DEVELOPMENT_PC:
            try:
                time.sleep(7)
                msg = EmailMultiAlternatives(email_subject,
                                             overal_result[j]['content'],
                                             'Helpdesk <%s>' % settings.DEFAULT_FROM_EMAIL,
                                             to=[overal_result[j]['owner_email']]
                                             )
                msg.content_subtype = 'html'
                msg.send()
                #print(overal_result[j])
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
        stats_utils.collect_statistics()
    except Exception as e:
        logger.warning(f'Unable to run daily statistics job, got error {e}')
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
