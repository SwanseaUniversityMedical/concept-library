#from cll import settings
from django.conf import settings
from clinicalcode.constants import *

def general_var(request):
    return {
            'MEDIA_URL': settings.MEDIA_URL,
            'CLL_READ_ONLY': settings.CLL_READ_ONLY,
            'SHOWADMIN': settings.SHOWADMIN,
            'BROWSABLEAPI': settings.BROWSABLEAPI,
            'LOGICAL_TYPES': LOGICAL_TYPES,
            'REGEX_TYPE_CHOICES': REGEX_TYPE_CHOICES,
            'DEV_PRODUCTION': settings.DEV_PRODUCTION,
            'IS_INSIDE_GATEWAY': settings.IS_INSIDE_GATEWAY,
            'enable_publish': settings.ENABLE_PUBLISH
            }

