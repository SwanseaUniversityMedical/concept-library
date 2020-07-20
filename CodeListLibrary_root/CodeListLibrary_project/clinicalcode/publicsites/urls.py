#from cll import settings
from django.conf import settings
from django.conf.urls import url

from views import (published_concept_details, 
                   published_concept_list, 
                   published_concept_codes_to_csv
                   )

urlpatterns = []

#======== Publish Concept ==================================
if settings.ENABLE_PUBLISH:
    urlpatterns = [
        url(r'^$', 
            published_concept_list, 
            name='published_concept_list_root'),
        
        url(r'^concepts/$', 
            published_concept_list, 
            name='published_concept_list'),
        
        url(r'^concepts/(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/details/$', 
            published_concept_details, 
            name='published_concept_details'),
        
        url(r'^concepts/(?P<concept_history_id>\d+)/export/codes/$', 
            published_concept_codes_to_csv, 
            name='published_concept_codes_to_csv')
        
    ]