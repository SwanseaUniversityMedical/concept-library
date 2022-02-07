"""cll URL Configuration

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
from clinicalcode import api
from clinicalcode.views import View
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.views import serve
from django.db import connection
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView


def db_table_exists(table_name):
    return table_name.lower() in [
        x.lower() for x in connection.introspection.table_names()
    ]


if settings.DEBUG:
    print("main url file ...")

current_brand = ""
current_brand = settings.CURRENT_BRAND
if settings.DEBUG:
    print("current_brand(settings.CURRENT_BRAND)= ", current_brand)

#--------------------------------------------------------------------
brands = []
if db_table_exists("clinicalcode_brand"):
    from clinicalcode.models import Brand
    brands = Brand.objects.values_list('name', flat=True)
    brands = [x.upper() for x in brands]

urlpatterns = []
#--------------------------------------------------------------------

# admin system
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^admin/', admin.site.urls),
    ]
#--------------------------------------------------------------------

# api
urlpatterns += [
    url(r'^api/v1/', include(('clinicalcode.api.urls', 'cll'),
                             namespace='api')),
]
#--------------------------------------------------------------------

# Add django site authentication urls (for login, logout, password management)
# enable login for all brands
for brand in brands:
    urlpatterns += [
        url(r"^" + brand + "/account/", include('django.contrib.auth.urls')),
    ]

# enable login for the main app
urlpatterns += [
    url(r'^account/', include('django.contrib.auth.urls')),
]
#--------------------------------------------------------------------

# index page
# enable index page for all brands
for brand in brands:
    urlpatterns += [
        url(r'^' + brand + '', View.index, name='concept_library_home'),
    ]
#--------------------------------------------------------------------

# clinical code application
# for the main app
urlpatterns += [
    url(r'^', include('clinicalcode.urls')),
]

#--------------------------------------------------------------------

# MEDIA_URL
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          view=cache_control(no_cache=True,
                                             must_revalidate=True)(serve))
