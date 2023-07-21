"""
WSGI config for cll project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ["DJANGO_SETTINGS_MODULE"] = "cll.settings"

path_prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if path_prj not in sys.path:
    sys.path.append(path_prj)

ver_env = "/var/www/concept_lib_sites/v1/CodeListLibrary_project/env/lib/python3.9/site-packages"
if ver_env not in sys.path:
    sys.path.append(ver_env)

application = get_wsgi_application()
