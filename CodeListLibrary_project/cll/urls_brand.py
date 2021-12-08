"""cll URL Configuration for Brands

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
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from clinicalcode import api
from django.views.generic import RedirectView

#from clinicalcode.models import Brand
from django.contrib.staticfiles.views import serve
from django.views.decorators.cache import cache_control

# Brands
if settings.DEBUG:
    print("BRANDING url file ...")


current_brand = ""
current_brand = settings.CURRENT_BRAND + "/"
if settings.IS_HDRUK_EXT == "1":
    current_brand = ""


    
if settings.DEBUG:
    print("current_brand(settings.CURRENT_BRAND)= ", current_brand)

#--------------------------------------------------------------------

urlpatterns = []
#--------------------------------------------------------------------

# admin system
if not settings.CLL_READ_ONLY:     
    urlpatterns += [
        url(r'^'+current_brand+'admin/', admin.site.urls ),
    ]
#--------------------------------------------------------------------

# api
urlpatterns += [
    url(r'^'+current_brand+'api/v1/', include(('clinicalcode.api.urls', 'cll'), namespace='api')),
]
#--------------------------------------------------------------------

# clinical code application
urlpatterns += [
    url(r'^'+current_brand+'', include('clinicalcode.urls')),
    ] 
#--------------------------------------------------------------------

# Add django site authentication urls (for login, logout, password management)
urlpatterns += [
    url(r'^'+current_brand+'account/', include('django.contrib.auth.urls')),
]

#--------------------------------------------------------------------

# MEDIA_URL
urlpatterns +=  static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, view=cache_control(no_cache=True, must_revalidate=True)(serve))

#--------------------------------------------------------------------

