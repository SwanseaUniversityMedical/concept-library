from importlib import import_module
from django.conf import settings
from django.urls import clear_url_caches, set_urlconf
from django.contrib import auth, messages
from django.shortcuts import redirect
from rest_framework.reverse import reverse
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.utils.deprecation import MiddlewareMixin

import os
import sys
import numbers
import importlib

from clinicalcode.models import Brand
from clinicalcode.entity_utils import gen_utils

class BrandMiddleware(MiddlewareMixin):
    '''
        Brand related middleware
            [ ...needs docs? ]
    '''
    def process_request(self, request):
        #---------------------------------
        # if the user is a member of  'ReadOnlyUsers' group, make READ-ONLY True
        if request.user.is_authenticated:
            CLL_READ_ONLY_org = self.get_env_value('CLL_READ_ONLY', cast='bool')
            settings.CLL_READ_ONLY = CLL_READ_ONLY_org

            if settings.DEBUG:
                print("CLL_READ_ONLY_org = ", str(CLL_READ_ONLY_org))

            if not settings.CLL_READ_ONLY:
                if (request.user.groups.filter(name='ReadOnlyUsers').exists()):
                    msg1 = "You are assigned as a Read-Only-User."
                    if request.session.get('read_only_msg', "") == "":
                        request.session['read_only_msg'] = msg1
                        messages.error(request, msg1)

                    settings.CLL_READ_ONLY = True
                    if settings.DEBUG:
                        print("settings.CLL_READ_ONLY = ", str(settings.CLL_READ_ONLY))

        #---------------------------------

        #if request.user.is_authenticated:
        #print "...........start..............."
        #brands = Brand.objects.values_list('name', flat=True)
        brands_list = Brand.all_names()
        current_page_url = request.path_info.lstrip('/')

        #print "**** get_host= " , str(request.get_host())

        request.IS_HDRUK_EXT = "0"
        settings.IS_HDRUK_EXT = "0"

        root = current_page_url.split('/')[0]
        if (request.get_host().lower().find('phenotypes.healthdatagateway') != -1 or
            request.get_host().lower().find('web-phenotypes-hdr') != -1):
            root = 'HDRUK'
            request.IS_HDRUK_EXT = "1"
            settings.IS_HDRUK_EXT = "1"

        root = root.upper()

        request.CURRENT_BRAND = ""
        settings.CURRENT_BRAND = ""

        request.CURRENT_BRAND_WITH_SLASH = ""
        settings.CURRENT_BRAND_WITH_SLASH = ""

        request.BRAND_OBJECT = {}
        settings.BRAND_OBJECT = {}
        
        request.SWAGGER_TITLE = "Concept Library API"
        settings.SWAGGER_TITLE = "Concept Library API"

        set_urlconf(None)
        request.urlconf = None
        urlconf = None
        urlconf = settings.ROOT_URLCONF

        request.session['all_brands'] = brands_list  #json.dumps(brands_list)
        request.session['current_brand'] = root

        do_redirect = False
        if root in brands_list:
            if settings.DEBUG:
                print("root=", root)

            settings.CURRENT_BRAND = root
            request.CURRENT_BRAND = root

            settings.CURRENT_BRAND_WITH_SLASH = "/" + root
            request.CURRENT_BRAND_WITH_SLASH = "/" + root

            brand_object = next((x for x in Brand.all_instances() if x.name.upper() == root.upper()), {})

            settings.BRAND_OBJECT = brand_object
            request.BRAND_OBJECT = brand_object
            if brand_object is not None and brand_object.site_title is not None and not gen_utils.is_empty_string(brand_object.site_title):
                request.SWAGGER_TITLE = brand_object.site_title + " API"
                settings.SWAGGER_TITLE = brand_object.site_title + " API"

            if not current_page_url.strip().endswith('/'):
                current_page_url = current_page_url.strip() + '/'

            if (request.get_host().lower().find('phenotypes.healthdatagateway') != -1 or
                request.get_host().lower().find('web-phenotypes-hdr') != -1):
                pass
            else:
                # # path_info does not change address bar urls
                request.path_info = '/' + '/'.join([root.upper()] + current_page_url.split('/')[1:])

            urlconf = "cll.urls_brand"
            set_urlconf(urlconf)
            request.urlconf = urlconf  # this is the python file path to custom urls.py file

        # redirect /{brand}/api/  to  /{brand}/api/v1/
        if current_page_url.strip().rstrip('/').split('/')[-1].lower() in ['api']:
            do_redirect = True
            current_page_url = current_page_url.strip().rstrip('/') + '/v1/'

        if urlconf in sys.modules:
            clear_url_caches()
            importlib.reload(sys.modules[urlconf])
            importlib.reload(import_module(urlconf))
            importlib.reload(sys.modules["clinicalcode.api.urls"])
            importlib.reload(import_module("clinicalcode.api.urls"))

        if settings.DEBUG:
            print(request.path_info)
            print(str(request.get_full_path()))

        # redirect /{brand}/api/  to  /{brand}/api/v1/ to appear in URL address bar
        if do_redirect:
            return redirect(reverse('api:root'))

        return None

    def chkReadOnlyUsers(self, request):
        if not settings.CLL_READ_ONLY:
            if (request.user.groups.filter(name='ReadOnlyUsers').exists()):
                messages.error(request, "You are assigned as a Read-Only-User. You can access only the ReadOnly website.")
                auth.logout(request)

        return None

    def strtobool(self, val):
        '''
            Converts str() to bool()
            [!] Required as distutil.util.strtobool no longer
                supported in Python v3.10+ and removed in v3.12+
        '''
        if isinstance(val, bool):
            return val

        if isinstance(val, numbers.Number):
            val = str(int(val))

        if not isinstance(val, str):
            raise ValueError('Invalid paramater %r, expected <str()> but got %r' % (val,type(val)))

        val = val.lower()
        if val in ('y', 'yes', 't', 'true', 'on', '1'):
            return 1
        elif val in ('n', 'no', 'f', 'false', 'off', '0'):
            return 0
        raise ValueError('Invalid truth value %r, expected one of (\'y/n\', \'yes/no\', \'t/f\', \'true/false\', \'on/off\', \'1/0\')' % (val,))

    def get_env_value(self, env_variable, cast=None):
        try:
            if cast == None:
                return os.environ[env_variable]
            elif cast == 'int':
                return int(os.environ[env_variable])
            elif cast == 'bool':
                return bool(self.strtobool(os.environ[env_variable]))
            else:
                return os.environ[env_variable]
        except KeyError:
            error_msg = 'Set the {} environment variable'.format(env_variable)
            raise ImproperlyConfigured(error_msg)
