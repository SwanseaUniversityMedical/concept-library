from django.conf import settings
from django.db.models import Model, Q
from email.mime.image import MIMEImage
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders

import os
import logging
import datetime

from clinicalcode.entity_utils import model_utils, gen_utils, constants
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity


User = get_user_model()
logger = logging.getLogger(__name__)


def send_invite_email(request, invite):
    brand_title = model_utils.try_get_brand_string(request.BRAND_OBJECT, 'site_title', default='Concept Library')

    owner_email = User.objects.filter(id=invite.user_id)
    if not owner_email.exists():
        return
    owner_email = owner_email.first().email

    if not owner_email or len(owner_email.strip()) < 1:
        return

    email_subject = f'{brand_title} - Organisation Invite'
    email_content = render_to_string(
        'clinicalcode/email/invite_email.html',
        { 
            'invite': {
                'uuid': invite.id
            } 
        },
        request=request
    )

    if not settings.IS_DEVELOPMENT_PC or settings.HAS_MAILHOG_SERVICE: 
        try:
            branded_imgs = get_branded_email_images(request.BRAND_OBJECT)

            msg = EmailMultiAlternatives(
                email_subject,
                email_content,
                settings.DEFAULT_FROM_EMAIL,
                to=[owner_email]
            )
            msg.content_subtype = 'related'
            msg.attach_alternative(email_content, "text/html")

            msg.attach(attach_image_to_email(branded_imgs.get('apple', 'img/email_images/apple-touch-icon.jpg'), 'mainlogo'))
            msg.attach(attach_image_to_email(branded_imgs.get('logo', 'img/email_images/combine.jpg'), 'sponsors'))
            msg.send()
            return True
        except BadHeaderError as error:
            logging.error(f'Failed to send invite emails to:\n- Targets: {owner_email}\n-Error: {str(error)}')
            return False
    else:
        logging.info(f'Scheduled invite emails sent:\n- Targets: {owner_email}')
        return True


def send_review_email_generic(request, data, message_from_reviewer=None):
    brand_title = model_utils.try_get_brand_string(request.BRAND_OBJECT, 'site_title', default='Concept Library')
    owner_email = User.objects.filter(id=data.get('entity_user_id', -1))
    owner_email = owner_email.first().email if owner_email and owner_email.exists() else ''

    staff_emails = data.get('staff_emails', [])
    staff_emails = staff_emails if isinstance(staff_emails, list) else []

    all_emails = set(staff_emails)
    if isinstance(owner_email, str) and not gen_utils.is_empty_string(owner_email):
        all_emails.add(owner_email)

    all_emails = list(all_emails)
    if len(all_emails) < 1:
        return False

    email_subject = '%s - %s: %s' % (brand_title, data['id'], data['message'])
    email_content = render_to_string(
        'clinicalcode/email/email_content.html',
        data,
        request=request
    )

    if not settings.IS_DEVELOPMENT_PC or settings.HAS_MAILHOG_SERVICE: 
        try:
            branded_imgs = get_branded_email_images(request.BRAND_OBJECT)

            msg = EmailMultiAlternatives(
                subject=email_subject,
                body=email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=all_emails
            )
            msg.content_subtype = 'related'
            msg.attach_alternative(email_content, "text/html")

            msg.attach(attach_image_to_email(branded_imgs.get('apple', 'img/email_images/apple-touch-icon.jpg'), 'mainlogo'))
            msg.attach(attach_image_to_email(branded_imgs.get('logo', 'img/email_images/combine.jpg'), 'sponsors'))
            msg.send()
            return True
        except BadHeaderError as error:
            logging.error(f'Failed to send review emails to:\n- Targets: {all_emails}\n-Error: {str(error)}')
            return False
    else:
        logging.info(f'Scheduled review emails sent:\n- Targets: {all_emails}')
        return True


def attach_image_to_email(image,cid):
    with open(finders.find(image), 'rb') as f:
        img = MIMEImage(f.read())
        img.add_header('Content-ID', '<{name}>'.format(name=cid))
        img.add_header('Content-Disposition', 'inline', filename=image)
    return img


def get_branded_email_images(brand=None):
    """
        Gets the brand-related e-mail image path(s)

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (dict) with key-value pairs specifying the `logo`, `apple`, and `favicon` path target(s)
    """
    if isinstance(brand, dict):
        path = brand.get('logo_path', None)
    elif isinstance(brand, Model):
        path = getattr(brand, 'logo_path', None) if hasattr(brand, 'logo_path') else None
    else:
        path = None

    if path is None or gen_utils.is_empty_string(path):
        path = settings.APP_LOGO_PATH

    return {
        'logo': os.path.join(path, 'header_logo.png'),
        'apple': os.path.join(path, 'apple-touch-icon.png'),
        'favicon': os.path.join(path, 'favicon-32x32.png'),
    }


def get_scheduled_email_to_send():
    week_dt = datetime.datetime.now() - datetime.timedelta(days=7)

    combined_pubs = PublishedGenericEntity.objects.filter(
        (Q(modified__gte=week_dt) | Q(modified__gte=week_dt))
        & Q(approval_status__in=[
            constants.APPROVAL_STATUS.PENDING.value,
            constants.APPROVAL_STATUS.REJECTED.value
        ])
    ) \
        .order_by('entity_id', '-entity_history_id', '-modified') \
        .distinct('entity_id', 'entity_history_id')

    email_content = []
    for _, pub in enumerate(combined_pubs):
        ent_id = pub.entity_id
        ent_ver = pub.entity_history_id

        entity = GenericEntity.history.filter(id=ent_id, history_id=ent_ver)
        entity = entity.first() if entity.exists() else None
        if entity is None:
            continue

        ent_name = entity.name
        ent_owner_id = entity.owner_id

        owner_email = User.objects.filter(id=ent_owner_id)
        owner_email = owner_email.first().email if owner_email.exists() else None
        if owner_email is None or gen_utils.is_empty_string(owner_email):
            continue

        review_status = ''
        review_message = ''
        if pub.approval_status == constants.APPROVAL_STATUS.PENDING.value:
            review_status = 'Pending'
            review_message = 'Your work is awaiting approval.'
        elif pub.approval_status == constants.APPROVAL_STATUS.REJECTED.value:
            review_status = 'Declined'
            review_message = 'Your work has been declined.'

        if gen_utils.is_empty_string(review_status):
            continue

        email_message = \
            '''
            <br><br>
            <strong>Entity:</strong><br>{id} - {name}<br><br>
            <strong>Decision:</strong><br>{status}<br><br>
            <strong>Reviewer message:</strong><br>{message}
            '''.format(
                id=ent_id,
                name=ent_name,
                status=review_status,
                message=review_message
            )

        email_content.append({
            'owner_id': ent_owner_id,
            'email_content': email_message,
            'entity_user_email': owner_email,
        })

    return email_content
