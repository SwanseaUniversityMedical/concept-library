from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from email.mime.image import MIMEImage

import datetime

from clinicalcode.models.Phenotype import Phenotype
from clinicalcode.models.PublishedPhenotype import PublishedPhenotype

def send_review_email_generic(request,data,message_from_reviewer=None):
    owner_email = User.objects.get(id=data['owner_id']).email
    if owner_email == '':
        return False

    email_subject = 'Concept Library - Data %s has been %s' % (data['id'], data['message'])
    email_content = render_to_string(
        'clinicalcode/email/email_content.html',
        data,
        request=request
    )
    
    if not settings.IS_DEVELOPMENT_PC: 
        try:
            msg = EmailMultiAlternatives(email_subject,
                                        email_content,
                                        settings.DEFAULT_FROM_EMAIL,
                                        to=[owner_email]
                                    )
            msg.content_subtype = 'related'
            msg.attach_alternative(email_content, "text/html")
            
            msg.attach(attach_image_to_email('img/email_images/apple-touch-icon.jpg','mainlogo'))
            msg.attach(attach_image_to_email('img/email_images/combine.jpg','combined'))

            msg.send()
            return True
        except BadHeaderError as error:
            print(error)
            return False
    else:
        print(email_content) 
        return True
    
def attach_image_to_email(image,cid):
    with open(finders.find(image), 'rb') as f:
        img = MIMEImage(f.read())
        img.add_header('Content-ID', '<{name}>'.format(name=cid))
        img.add_header('Content-Disposition', 'inline', filename=image)
    
    return img

def get_scheduled_email_to_send():
    HDRUK_pending_phenotypes = PublishedPhenotype.objects.filter(approval_status=1)
    HDRUK_declined_phenotypes = PublishedPhenotype.objects.filter(approval_status=3)

    combined_list = list(HDRUK_pending_phenotypes.values()) + list(HDRUK_declined_phenotypes.values())
    result = {'date':datetime.datetime.now(),
            'phenotype_count': len(combined_list),
            'data':[]
            }

    for i in range(len(combined_list)):
        data = {
            'id': i+1,
            'phenotype_id':combined_list[i]['phenotype_id'],
            'phenotype_history_id':combined_list[i]['phenotype_history_id'],
            'approval_status':combined_list[i]['approval_status'],
            'owner_id':combined_list[i]['created_by_id'],
        }
        result['data'].append(data)

    email_content = []
    for i in range(len(result['data'])):
        phenotype = Phenotype.objects.get(pk=result['data'][i]['phenotype_id'], owner_id=result['data'][i]['owner_id'])
        phenotype_id = phenotype.id

        phenotype_name = phenotype.name
        phenotype_owner_id = phenotype.owner_id

        review_decision = ''
        review_message = ''
        if result['data'][i]['approval_status'] == 1:
            review_decision = 'Pending'
            review_message = "Phenotype is waiting to be approved"
        elif result['data'][i]['approval_status'] == 3:
            review_decision = 'Declined'
            review_message = 'Phenotype has been declined'

        owner_email = User.objects.get(id=phenotype_owner_id).email
        if owner_email == '':
            return False

        email_message = '''<br><br>
                 <strong>Phenotype:</strong><br>{id} - {name}<br><br>
                 <strong>Decision:</strong><br>{decision}<br><br>
                 <strong>Reviewer message:</strong><br>{message}
                 '''.format(id=phenotype_id, name=phenotype_name, decision=review_decision, message=review_message)

        email_content.append({'owner_id': phenotype_owner_id, 'owner_email': owner_email, 'email_content': email_message})

    return email_content
