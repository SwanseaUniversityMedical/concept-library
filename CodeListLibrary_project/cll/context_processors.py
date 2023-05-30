#from cll import settings
from clinicalcode.constants import *
from django.conf import settings
from clinicalcode.api.views.View import get_canonical_path
from clinicalcode.entity_utils import constants

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
        'IS_PRODUCTION_SERVER': (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC and not settings.IS_INSIDE_GATEWAY),  #  and not settings.DEBUG
        'IS_DEMO': settings.IS_DEMO,
        'IS_DEVELOPMENT_PC': settings.IS_DEVELOPMENT_PC,
        'SHOW_COOKIE_ALERT': settings.SHOW_COOKIE_ALERT,
        'IS_HDRUK_EXT': settings.IS_HDRUK_EXT,
        'CANONICAL_PATH': get_canonical_path(request),
        'APPROVED_STATUS_DICT': {e.name: e.value for e in constants.APPROVAL_STATUS}
    }
    
  