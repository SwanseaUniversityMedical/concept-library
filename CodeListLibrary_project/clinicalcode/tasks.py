from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core import management
from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.test.client import RequestFactory

from clinicalcode.entity_utils import stats_utils, email_utils, gen_utils, oc_utils

@shared_task(bind=True)
def send_message_test(self):
    return 'test message'

@shared_task(name="review_email_background_task")
def send_review_email(request, data):
    email_utils.send_review_email_generic(request, data)
    return f"Email sent - {data['id']} with name {data['entity_name']} and owner_id {data['entity_user_id']}"

@shared_task(bind=True)
def send_scheduled_email():
    email_subject = 'Weekly Email'
    email_content = email_utils.get_scheduled_email_to_send()

    owner_ids = list(set([c['owner_id'] for c in email_content]))
    owner_email = [next((c.get('owner_email') for c in email_content if c.owner_id == x), None) for x in owner_ids]

    overall_result = []
    for i, oid in enumerate(owner_ids):
        addr = owner_email[i]
        if addr is None or gen_utils.is_empty_string(addr):
            continue

        overall_result.append({
            'owner_id': oid, 
            'owner_email': addr, 
            'content': ''.join([
                c.get('email_content')
                for c in email_content
                if c.get('owner_id') == oid
            ]),
        })

    for i, res in enumerate(overall_result):
        if not settings.IS_DEVELOPMENT_PC or settings.HAS_MAILHOG_SERVICE:
            try:
                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=res.get('content'),
                    from_email='Helpdesk <%s>' % settings.DEFAULT_FROM_EMAIL,
                    to=[res.get('owner_email')]
                )

                msg.content_subtype = 'html'
                msg.send()
            except BadHeaderError:
                continue

    return True, overall_result

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

@shared_task(bind=True)
def run_opencodelist_sync(self):
    """
      Attempts to sync the OpenCodelist phenotypes with those found through the OpenCodelist phenotypes API
    """
    oc_utils.sync_opencodelist_phenotypes()
    return True
