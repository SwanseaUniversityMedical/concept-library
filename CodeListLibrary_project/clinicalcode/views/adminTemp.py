from django.contrib.auth.mixins import LoginRequiredMixin #, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse_lazy, reverse
from django.db import transaction #, models, IntegrityError
from django.http import HttpResponseRedirect #, StreamingHttpResponse, HttpResponseForbidden
from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView #, DeleteView
from django.contrib.auth.models import User
from django.conf import settings
from simple_history.models import HistoricalRecords
import time

#from ..forms.ConceptForms import ConceptForm, ConceptUploadForm
from ..models import *
from View import *
from .. import db_utils
from .. import utils
from ..permissions import *
from django.utils.timezone import now
from datetime import datetime

logger = logging.getLogger(__name__)

from django.core.exceptions import  PermissionDenied
from django.db import connection, connections #, transaction
import json
import os


@login_required    
def api_remove_data(request):
    if not request.user.is_superuser:
        raise PermissionDenied
        
    if settings.CLL_READ_ONLY:
        raise PermissionDenied
         

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
            return render(request, 'clinicalcode/adminTemp/adminTemp.html', 
                          { }
                        )
        
    elif request.method == 'POST':  
        if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
            code =  request.POST.get('code')
            if code.strip()!="nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
                raise PermissionDenied
        
            rowsAffected = {}
            
    
    #             
            concepts = Concept.objects.filter(owner=request.user)
            for c in concepts:
                rowsAffected[c.id] = "concept: " + c.name + " :: deleted"
                c.delete()
    
            rowsAffected["**********************************"] = "**********************************"
    
    
            workingsets = WorkingSet.objects.filter(owner=request.user)
            for ws in workingsets:
                rowsAffected[ws.id] = "working set: " + ws.name + ":: deleted"
                ws.delete()
    
            rowsAffected["**********************************"] = "**********************************"
    
    
    
            
            return render(request, 
                        'clinicalcode/adminTemp/adminTemp.html', 
                        {   'pk': -10,
                            'strSQL': {},
                            'rowsAffected' : rowsAffected
                        }
                        )
