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

            concepts = Concept.history.filter(owner=request.user)
            for c in concepts:
                rowsAffected[c.id] = "concept: " + c.name + " :: deleted"
                c.delete()

            rowsAffected["**********************************"] = "**********************************"
    
    
            workingsets = WorkingSet.objects.filter(owner=request.user)
            for ws in workingsets:
                rowsAffected[ws.id] = "working set: " + ws.name + ":: deleted"
                ws.delete()
             
            workingsets = WorkingSet.history.filter(owner=request.user)
            for ws in workingsets:
                rowsAffected[ws.id] = "working set: " + ws.name + ":: deleted"
                ws.delete()
    
            rowsAffected["**********************************"] = "**********************************"
            
            phenotypes = Phenotype.objects.filter(owner=request.user)
            for ph in phenotypes:
                rowsAffected[ph.id] = "phenotype: " + ph.name + ":: deleted"
                ph.delete()
             
            phenotypes = Phenotype.history.filter(owner=request.user)
            for ph in phenotypes:
                rowsAffected[ph.id] = "phenotype: " + ph.name + ":: deleted"
                ph.delete()
            
            rowsAffected["**********************************"] = "**********************************"
    
    
    
            
            return render(request, 
                        'clinicalcode/adminTemp/adminTemp.html', 
                        {   'pk': -10,
                            'strSQL': {},
                            'rowsAffected' : rowsAffected
                        }
                        )
        
@login_required    
def moveTags(request):
    if not request.user.is_superuser:
        raise PermissionDenied
        
    if settings.CLL_READ_ONLY:
        raise PermissionDenied
         

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
            return render(request, 'clinicalcode/adminTemp/moveTags.html', 
                          { }
                        )
        
    elif request.method == 'POST':  
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
            code =  request.POST.get('code')
            if code.strip()!="nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
                raise PermissionDenied
        
            rowsAffected = {}
            
    
                 
#             ######################################################################
#             # move phenotype tags as attribute
#             distinct_phenotypes_with_tags = PhenotypeTagMap.objects.all().distinct('phenotype_id')
#             for dp in distinct_phenotypes_with_tags:
#                 #print "*************"
#                 #print dp.phenotype_id
#                 hisp = Phenotype.history.filter(id=dp.phenotype_id)
#                 for hp in hisp:
#                     #print hp.id, "...", hp.history_id
#                     phenotype_tags_history = db_utils.getHistoryTags_Phenotype(hp.id, hp.history_date)
#                     if phenotype_tags_history:
#                         phenotype_tag_list = [i['tag_id'] for i in phenotype_tags_history if 'tag_id' in i]
#                     else:
#                         phenotype_tag_list = []
#                     #print phenotype_tag_list
#                     with connection.cursor() as cursor:
#                         sql = """ UPDATE clinicalcode_historicalphenotype 
#                                     SET tags = '{""" + ','.join([str(i) for i in phenotype_tag_list]) + """}'
#                                     WHERE id="""+str(hp.id)+""" and history_id="""+str(hp.history_id)+""";
#                              """ 
#                         cursor.execute(sql)
#                         if hp.history_id == int(Phenotype.objects.get(pk=hp.id).history.latest().history_id):
#                             sql2 = """ UPDATE clinicalcode_phenotype 
#                                     SET tags = '{""" + ','.join([str(i) for i in phenotype_tag_list]) + """}'
#                                     WHERE id="""+str(hp.id)+"""  ;
#                              """ 
#                             cursor.execute(sql2)
#                              
#                             rowsAffected[hp.id] = "phenotype: " + hp.name + ":: tags moved"

                 
            ######################################################################
            # move concept tags as attribute
            distinct_concepts_with_tags = ConceptTagMap.objects.all().distinct('concept_id')
            for dp in distinct_concepts_with_tags:
                #print "*************"
                #print dp.concept_id
                hisp = Concept.history.filter(id=dp.concept_id)
                for hp in hisp:
                    #print hp.id, "...", hp.history_id
                    concept_tags_history = db_utils.getHistoryTags(hp.id, hp.history_date)
                    if concept_tags_history:
                        concept_tag_list = [i['tag_id'] for i in concept_tags_history if 'tag_id' in i]
                    else:
                        concept_tag_list = []
                    #print concept_tag_list
                    with connection.cursor() as cursor:
                        sql = """ UPDATE clinicalcode_historicalconcept 
                                    SET tags = '{""" + ','.join([str(i) for i in concept_tag_list]) + """}'
                                    WHERE id="""+str(hp.id)+""" and history_id="""+str(hp.history_id)+""";
                             """ 
                        cursor.execute(sql)
                        if hp.history_id == int(Concept.objects.get(pk=hp.id).history.latest().history_id):
                            sql2 = """ UPDATE clinicalcode_concept 
                                    SET tags = '{""" + ','.join([str(i) for i in concept_tag_list]) + """}'
                                    WHERE id="""+str(hp.id)+"""  ;
                             """ 
                            cursor.execute(sql2)
                            
                            rowsAffected[hp.id] = "concept: " + hp.name + ":: tags moved"

    
        
    
            
            return render(request, 
                        'clinicalcode/adminTemp/moveTags.html', 
                        {   'pk': -10,
                            'strSQL': {},
                            'rowsAffected' : rowsAffected
                        }
                        )
            
                        
            
# @login_required    
# def api_remove_longIDfromName(request):
#     if not request.user.is_superuser:
#         raise PermissionDenied
#         
#     if settings.CLL_READ_ONLY:
#         raise PermissionDenied
#          
# 
#     if request.method == 'GET':
#         if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
#             return render(request, 'clinicalcode/adminTemp/api_remove_longIDfromName.html', 
#                           { }
#                         )
#          
#     elif request.method == 'POST':  
#         if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
#             code =  request.POST.get('code')
#             if code.strip()!="nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
#                 raise PermissionDenied
#          
#             rowsAffected = {}
#              
#           
#             #######################################################################
#  
#             from django.db import connection, connections #, transaction
#             
#             # remove long ID from concept name / title
#             hisp = Concept.history.all()
#             for hp in hisp:
#                 print hp.id, "...", hp.history_id
#                 print hp.name
#                 print "..................."
#                 if hp.name.find(' - ') != -1:
#                     newname = ' - '.join(hp.name.split(' - ')[1:])
#                     newname = newname.replace("'", "''")
#                     print newname
#                     with connection.cursor() as cursor:
#                         sql = """ UPDATE clinicalcode_historicalconcept 
#                                     SET  name = '""" + newname + """'  
#                                     WHERE id="""+str(hp.id)+""" and history_id="""+str(hp.history_id)+""";
#                              """ 
#                         cursor.execute(sql)
#                         if hp.history_id == int(Concept.objects.get(pk=hp.id).history.latest().history_id):
#                             sql2 = """ UPDATE clinicalcode_concept 
#                                     SET name = '""" + newname + """' 
#                                     WHERE id="""+str(hp.id)+"""  ;
#                              """ 
#                             cursor.execute(sql2)
#                       
#                 print "-------------"
#             
#             ######################################################################
#             
#             # remove long ID from phenotype name / title
#             hisp = Phenotype.history.all()
#             for hp in hisp:
#                 print hp.id, "...", hp.history_id
#                 print hp.name
#                 print "..................."
#                 if hp.name.find(' - ') != -1:
#                     newname = ' - '.join(hp.name.split(' - ')[1:])
#                     newname = newname.replace("'", "''")
#                     print newname
#                     with connection.cursor() as cursor:
#                         sql = """ UPDATE clinicalcode_historicalphenotype 
#                                     SET title = '""" + newname + """' ,  name = '""" + newname + """'  
#                                     WHERE id="""+str(hp.id)+""" and history_id="""+str(hp.history_id)+""";
#                              """ 
#                         cursor.execute(sql)
#                         if hp.history_id == int(Phenotype.objects.get(pk=hp.id).history.latest().history_id):
#                             sql2 = """ UPDATE clinicalcode_phenotype 
#                                     SET title = '""" + newname + """' ,  name = '""" + newname + """' 
#                                     WHERE id="""+str(hp.id)+"""  ;
#                              """ 
#                             cursor.execute(sql2)
#                           
#                     print "-------------"
#             
#             
#             
#             return render(request, 
#                    'clinicalcode/adminTemp/api_remove_longIDfromName.html', 
#                    {   'pk': -10,
#                        'strSQL': {},
#                        'rowsAffected' : rowsAffected
#                    }
#                    )
#             
#             
