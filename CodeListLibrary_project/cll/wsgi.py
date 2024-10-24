"""
WSGI config for cll project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""
from django.core.wsgi import get_wsgi_application

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cll.settings")

path_prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path_prj not in sys.path:
    sys.path.append(path_prj)
    sys.path.append(os.path.join(path_prj, 'cll'))
    sys.path.append(os.path.join(path_prj, 'clinicalcode'))

ver_env = "/usr/local/lib/python3.10/site-package"
if ver_env not in sys.path:
    sys.path.append(ver_env)

application = get_wsgi_application()
