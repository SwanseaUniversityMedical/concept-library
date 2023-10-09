"""
    CLL URL Configuration for Brands

    The `urlpatterns` list routes URLs to views. For more information please see:
        - https://docs.djangoproject.com/en/1.10/topics/http/urls/
    
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
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView

#--------------------------------------------------------------------
# Brands
current_brand = ""
current_brand = settings.CURRENT_BRAND + "/"
if settings.IS_HDRUK_EXT == "1":
    current_brand = ""

if settings.DEBUG:
    print("BRANDING url file ...")
    print("current_brand(settings.CURRENT_BRAND)=", current_brand)

#--------------------------------------------------------------------
# Urls
urlpatterns = [
    # api
    url(r'^' + current_brand + 'api/v1/', include(('clinicalcode.api.urls', 'cll'), namespace='api')),

    # login
    url(r'^' + current_brand + 'account/', include('django.contrib.auth.urls')),

    # app urls
    url(r'^' + current_brand + '', include('clinicalcode.urls')),
]

# Media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, view=cache_control(no_cache=True, must_revalidate=True)(serve))

# Admin system
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^' + current_brand + 'admin/', admin.site.urls),
    ]
