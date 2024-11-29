"""
    CLL URL Configuration

    The `urlpatterns` list routes URLs to views. For more information please see:
        https://docs.djangoproject.com/en/1.10/topics/http/urls/
    
    Examples:
        Function views
            1. Add an import:  from my_app import views
            2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')

        Class-based views
            1. Add an import:  from other_app.views import Home
            2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
        
        Including another URLconf
            1. Import the include() function: from django.conf.urls import url, include
            2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))

"""

from django.conf import settings
from django.urls import re_path as url
from django.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.views import serve
from django.db import connection
from django.views.decorators.cache import cache_control

from clinicalcode.views import View

#--------------------------------------------------------------------
# Utils
def db_table_exists(table_name):
    return table_name.lower() in [x.lower() for x in connection.introspection.table_names()]

#--------------------------------------------------------------------
# Brands
current_brand = ""
current_brand = settings.CURRENT_BRAND
if settings.DEBUG:
    print("main url file ...")
    print("current_brand(settings.CURRENT_BRAND)=", current_brand)

brands = []
if db_table_exists("clinicalcode_brand"):
    from clinicalcode.models import Brand
    brands = Brand.objects.values_list('name', flat=True)
    brands = [x.upper() for x in brands]

#--------------------------------------------------------------------
# URLs
urlpatterns = []

# Media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, view=cache_control(no_cache=True, must_revalidate=True)(serve))

# Add django site authentication urls (for login, logout, password management)
# and enable login for all brands
for brand in brands:
    urlpatterns += [
        # index for each brand
        url(r'^' + brand + '', View.index, name='concept_library_home'),

        # login for each brand
        url(r"^" + brand + "/account/", include('django.contrib.auth.urls')),
    ]

# Application URLs
urlpatterns = [
    # api
    url(r'^api/v1/', include(('clinicalcode.api.urls', 'cll'), namespace='api')),

    # login
    url(r'^account/', include('django.contrib.auth.urls')),

    # app urls
    url(r'^', include('clinicalcode.urls')),
    # url('', include('django_prometheus.urls')),

]

#--------------------------------------------------------------------
# Admin
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^admin/', admin.site.urls),
    ]
