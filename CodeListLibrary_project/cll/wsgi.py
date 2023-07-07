"""
WSGI config for cll project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
import sys

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

# if 'test' in sys.argv:
#     # if a command contains read_only phrase at the end, then read cll.read_only_test_settings otherwise cll.test_settings
#     if 'read_only' in sys.argv[-1]:
#         os.environ["DJANGO_SETTINGS_MODULE"] = "cll.read_only_test_settings"
#         print("<<<<<<<  WSGI Running read-Only Tests   >>>>>>>")
#     else:
#         os.environ["DJANGO_SETTINGS_MODULE"] = "cll.test_settings"
#         print("<<<<<<< WSGI  Running Tests  >>>>>>>")
#
# else:
#     os.environ["DJANGO_SETTINGS_MODULE"] = "cll.settings"

os.environ["DJANGO_SETTINGS_MODULE"] = "cll.settings"

path_prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# if os.name.lower()=="nt":
#     path_prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# else:
#     path_prj = "/var/www/codelistlibrary/CodeListLibrary_project"

if path_prj not in sys.path:
    sys.path.append(path_prj)

ver_env = "/var/www/concept_lib_sites/v1/cllvirenv_v1/lib/python2.7/site-packages"
if ver_env not in sys.path:
    sys.path.append(ver_env)

application = get_wsgi_application()
application = WhiteNoise(application, root=os.path.join(settings.BASE_DIR, 'cll/static'))
