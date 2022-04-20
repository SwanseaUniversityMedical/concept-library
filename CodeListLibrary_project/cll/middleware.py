import distutils
import importlib
import os
import sys
from distutils import util
#from cll import settings
from importlib import import_module

from clinicalcode.models import Brand
from decouple import Config, Csv, RepositoryEnv
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import auth, messages
#import json
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import clear_url_caches, get_urlconf, set_urlconf
from django.utils.deprecation import MiddlewareMixin
from rest_framework.reverse import reverse


class brandMiddleware(MiddlewareMixin):

    def process_request(self, request):
        #---------------------------------
        # if the user is a member of  'ReadOnlyUsers' group, make READ-ONLY True
        if request.user.is_authenticated:
            CLL_READ_ONLY_org = self.get_env_value('CLL_READ_ONLY', cast='bool')
            if settings.DEBUG:
                print("CLL_READ_ONLY_org = ", str(CLL_READ_ONLY_org))
            settings.CLL_READ_ONLY = CLL_READ_ONLY_org
            if settings.DEBUG:
                print("CLL_READ_ONLY_org (after) = ", str(CLL_READ_ONLY_org))

            #self.chkReadOnlyUsers(request)
            if not settings.CLL_READ_ONLY:
                if (request.user.groups.filter(name='ReadOnlyUsers').exists()):
                    msg1 = "You are assigned as a Read-Only-User."
                    if request.session.get('read_only_msg', "") == "":
                        request.session['read_only_msg'] = msg1
                        messages.error(request, msg1)

                    settings.CLL_READ_ONLY = True
                    if settings.DEBUG:
                        print("settings.CLL_READ_ONLY = ",
                              str(settings.CLL_READ_ONLY))

    #---------------------------------

    #if request.user.is_authenticated:
    #print "...........start..............."
    #brands = Brand.objects.values_list('name', flat=True)
        brands = Brand.objects.all()
        brands_list = [x.upper() for x in list(brands.values_list('name', flat=True)) ]
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

        request.BRAND_GROUPS = []
        userBrands = []
        all_brands_groups = []
        for b in brands:
            b_g = {}
            groups = b.groups.all()
            if (any(x in request.user.groups.all() for x in groups) or b.owner == request.user):
                userBrands.append(b.name.upper())

            b_g[b.name.upper()] = list(groups.values_list('name', flat=True))
            all_brands_groups.append(b_g)

        request.session['user_brands'] = userBrands  #json.dumps(userBrands)
        request.BRAND_GROUPS = all_brands_groups

        do_redirect = False
        if root in brands_list:
            if settings.DEBUG: print("root=", root)
            settings.CURRENT_BRAND = root
            request.CURRENT_BRAND = root

            settings.CURRENT_BRAND_WITH_SLASH = "/" + root
            request.CURRENT_BRAND_WITH_SLASH = "/" + root

            brand_object = Brand.objects.get(name__iexact=root)
            settings.BRAND_OBJECT = brand_object
            request.BRAND_OBJECT = brand_object
            if brand_object.site_title is not None:
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


#                 print "-------"
#                 print current_page_url
#                 print current_page_url.split('/')[1:]
#                 print '/'.join([root.upper()] + current_page_url.split('/')[1:])
#                 print request.path_info
#                 print "-------"

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

        # Do NOT allow concept create under HDRUK - for now
        if (str(request.get_full_path()).upper().replace('/', '') == "/HDRUK/concepts/create/".upper().replace('/', '') or
            ((request.get_host().lower().find('phenotypes.healthdatagateway') != -1 or request.get_host().lower().find('web-phenotypes-hdr') != -1)
             and str(request.get_full_path()).upper().replace('/', '').endswith('/concepts/create/'.upper().replace('/', '')))):

            raise PermissionDenied

        # redirect /{brand}/api/  to  /{brand}/api/v1/ to appear in URL address bar
        if do_redirect:
            return redirect(reverse('api:root'))

        #print "get_urlconf=" , str(get_urlconf())
        #print "settings.CURRENT_BRAND=" , settings.CURRENT_BRAND
        #print "request.CURRENT_BRAND=" , request.CURRENT_BRAND

        #print "...........end..............."

        return None

    def chkReadOnlyUsers(self, request):

        if not settings.CLL_READ_ONLY:
            if (request.user.groups.filter(name='ReadOnlyUsers').exists()):
                messages.error(request,
                    "You are assigned as a Read-Only-User. You can access only the ReadOnly website."
                )
                auth.logout(request)

        return None

    def get_env_value(self, env_variable, cast=None):
        try:
            if cast == None:
                return os.environ[env_variable]
            elif cast == 'int':
                return int(os.environ[env_variable])
            elif cast == 'bool':
                return bool(distutils.util.strtobool(os.environ[env_variable]))
            else:
                return os.environ[env_variable]
        except KeyError:
            error_msg = 'Set the {} environment variable'.format(env_variable)
            raise ImproperlyConfigured(error_msg)
        
        
