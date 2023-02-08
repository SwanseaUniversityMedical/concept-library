import time
from datetime import datetime
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction  # , models, IntegrityError
from django.http import HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string
#from django.core.urlresolvers import reverse_lazy, reverse
from django.urls import reverse, reverse_lazy
from django.utils.timezone import now
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView  # , DeleteView
from simple_history.models import HistoricalRecords

from .. import db_utils, utils
#from ..forms.ConceptForms import ConceptForm, ConceptUploadForm
from ..models import *
from ..permissions import *
from .View import *
from clinicalcode.models.GenericEntity import GenericEntity
from ..constants import *
from clinicalcode.models import Template

logger = logging.getLogger(__name__)

import json
import os

from django.core.exceptions import PermissionDenied
from django.db import connection, connections  # , transaction
from rest_framework.reverse import reverse
        
        
@login_required
def api_remove_data(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            return render(request, 'clinicalcode/adminTemp/adminTemp.html', 
                          {'url': reverse('json_adjust_phenotype'),
                           'action_title': 'Delete API Data'
                        }
                        )

    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            code = request.POST.get('code')
            if code.strip() != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
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

            return render(request, 'clinicalcode/adminTemp/adminTemp.html', {
                'pk': -10,
                'strSQL': {},
                'rowsAffected': rowsAffected,
                'action_title': 'Delete API Data'
            })
            
"""
@login_required
def json_adjust_phenotype(request):
    # not needed anymore
    raise PermissionDenied

    if not request.user.is_superuser:
        raise PermissionDenied

    if settings.CLL_READ_ONLY or (not settings.IS_DEVELOPMENT_PC):
        raise PermissionDenied

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            return render(request, 'clinicalcode/adminTemp/adminTemp.html', 
                          {'url': reverse('json_adjust_phenotype')
                           })
            
    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            code = request.POST.get('code')
            if code.strip() != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
                raise PermissionDenied

            rowsAffected = {}


            ######################################################################

            hisp = Phenotype.history.filter(id__gte=0)  #.exclude(id__in=[1026])
            for hp in hisp:
                if hp.concept_informations:
                    concept_informations = json.loads(hp.concept_informations)
                    hp.concept_informations = concept_informations
                    hp.save()

                    if hp.history_id == int(Phenotype.objects.get(pk=hp.id).history.latest().history_id):
                        p0 = Phenotype.objects.get(id=hp.id)
                        p0.concept_informations = concept_informations
                        p0.save_without_historical_record()
        
                        rowsAffected[hp.id] = "phenotype: " + hp.name + ":: json adjusted"
            
            
            
            
            
            return render(request,
                        'clinicalcode/adminTemp/adminTemp.html',
                        {   'pk': -10,
                            'strSQL': {},
                            'rowsAffected' : rowsAffected
                        }
                        )
"""

"""            
@login_required
def json_adjust_workingset(request):
    # not needed anymore
    raise PermissionDenied

    if not request.user.is_superuser:
        raise PermissionDenied

    if settings.CLL_READ_ONLY or (not settings.IS_DEVELOPMENT_PC):
        raise PermissionDenied

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            return render(request, 'clinicalcode/adminTemp/adminTemp.html', 
                          {'url': reverse('json_adjust_workingset')
                           })
            
    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            code = request.POST.get('code')
            if code.strip() != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
                raise PermissionDenied

            rowsAffected = {}


            ######################################################################

            ws_hitory = WorkingSet.history.filter(id__gte=0)  #.exclude(id__in=[1026])
            for ws in ws_hitory:
                if ws.concept_informations:
                    concept_informations = json.loads(ws.concept_informations)
                    ws.concept_informations = concept_informations
                    ws.save()

                    if ws.history_id == int(WorkingSet.objects.get(pk=ws.id).history.latest().history_id):
                        wso = WorkingSet.objects.get(id=ws.id)
                        wso.concept_informations = concept_informations
                        wso.save_without_historical_record()
        
                        rowsAffected[ws.id] = "working set: " + ws.name + ":: json adjusted"
            
            
            
            
            
            return render(request,
                        'clinicalcode/adminTemp/adminTemp.html',
                        {   'pk': -10,
                            'strSQL': {},
                            'rowsAffected' : rowsAffected
                        }
                        )
            
"""
                        
# @login_required
# def moveDataSources(request):
#     # not needed anymore
#     raise PermissionDenied
#
#     if not request.user.is_superuser:
#         raise PermissionDenied
#
#     if settings.CLL_READ_ONLY:
#         raise PermissionDenied
#
#     if request.method == 'GET':
#         if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
#             return render(request, 'clinicalcode/adminTemp/moveDataSources.html', {})
#
#     elif request.method == 'POST':
#         if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
#             code = request.POST.get('code')
#             if code.strip() != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
#                 raise PermissionDenied
#
#             rowsAffected = {}
#


            ######################################################################
            # # move phenotype data-sources as an attribute
            # distinct_phenotypes_with_ds = PhenotypeDataSourceMap.objects.all().distinct('phenotype_id')
            # for dp in distinct_phenotypes_with_ds:
            #     #print "*************"
            #     #print dp.phenotype_id
            #     hisp = Phenotype.history.filter(id=dp.phenotype_id)
            #     for hp in hisp:
            #         #print hp.id, "...", hp.history_id
            #         ph_DataSources_history = db_utils.getHistoryDataSource_Phenotype(hp.id, hp.history_date)
            #         if ph_DataSources_history:
            #             ph_DataSources_list = [i['datasource_id'] for i in ph_DataSources_history if 'datasource_id' in i]
            #         else:
            #             ph_DataSources_list = []
            #         #print ph_DataSources_list
            #         with connection.cursor() as cursor:
            #             sql = """ UPDATE clinicalcode_historicalphenotype
            #                         SET data_sources = '{""" + ','.join([str(i) for i in ph_DataSources_list]) + """}'
            #                         WHERE id="""+str(hp.id)+""" and history_id="""+str(hp.history_id)+""";
            #                  """
            #             cursor.execute(sql)
            #             if hp.history_id == int(Phenotype.objects.get(pk=hp.id).history.latest().history_id):
            #                 sql2 = """ UPDATE clinicalcode_phenotype
            #                         SET data_sources = '{""" + ','.join([str(i) for i in ph_DataSources_list]) + """}'
            #                         WHERE id="""+str(hp.id)+"""  ;
            #                  """
            #                 cursor.execute(sql2)
            #
            #                 rowsAffected[hp.id] = "phenotype: " + hp.name + ":: data_sources moved"
            #
            #
            #
            #
            #
            # return render(request,
            #             'clinicalcode/adminTemp/moveDataSources.html',
            #             {   'pk': -10,
            #                 'strSQL': {},
            #                 'rowsAffected' : rowsAffected
            #             }
            #             )

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


def update_concept_tags_from_phenotype_tags():
    return 

    phenotypes = Phenotype.objects.all()
    for p in phenotypes:
        concept_id_list = [x['concept_id'] for x in p.concept_informations]
        concept_hisoryid_list = [x['concept_version_id'] for x in p.concept_informations]
        concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list)

        for c in concepts:
            with connection.cursor() as cursor:
                sql = """ UPDATE clinicalcode_historicalconcept 
                            SET tags = '{""" + ','.join([str(i) for i in p.tags ]) + """}'
                            WHERE id=""" + str(c.id) + """ and history_id=""" + str(c.history_id) + """;
                    """
                cursor.execute(sql)
                sql2 = """ UPDATE clinicalcode_concept 
                            SET tags = '{""" + ','.join([str(i) for i in p.tags]) + """}'
                            WHERE id=""" + str(c.id) + """  ;
                    """
                cursor.execute(sql2)

                print(("phenotype/concept: " + p.name + "/" + c.name + ":: tags moved"))


@login_required
def check_concepts_not_associated_with_phenotypes(request):

    phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(request, exclude_deleted=False)
    phenotypes_id = db_utils.get_list_of_visible_entity_ids(phenotypes, return_id_or_history_id="id")

    concepts_ids_in_phenotypes = []
    for p in phenotypes_id:
        phenotype = Phenotype.objects.get(pk=p)
        if phenotype.concept_informations:
            concept_id_list = [x['concept_id'] for x in phenotype.concept_informations]    
            concepts_ids_in_phenotypes = concepts_ids_in_phenotypes + concept_id_list

    concepts_ids_in_phenotypes = set(concepts_ids_in_phenotypes)

    concepts = db_utils.get_visible_live_or_published_concept_versions(request, exclude_deleted=False)

    all_concepts_ids = db_utils.get_list_of_visible_entity_ids(concepts, return_id_or_history_id="id")

    result = all(elem in concepts_ids_in_phenotypes for elem in all_concepts_ids)
    if result:
        messages.success(request, "Yes, all concepts are associated with phenotypes.")
    else:
        messages.warning(request, "No, NOT all concepts are associated with phenotypes.")

    unasscoiated_concepts_ids = list(set(all_concepts_ids) - set(concepts_ids_in_phenotypes))

    unasscoiated_concepts = Concept.objects.filter(id__in=unasscoiated_concepts_ids).order_by('id')

    return render(request,
                  'clinicalcode/adminTemp/concepts_not_in_phenotypes.html', {
                      'count': unasscoiated_concepts.count(),
                      'concepts': unasscoiated_concepts
                  })




@login_required
def populate_collections_tags(request):
    # not needed anymore
    raise PermissionDenied

    # if not request.user.is_superuser:
    #     raise PermissionDenied
    #
    # if settings.CLL_READ_ONLY: # or (not settings.IS_DEVELOPMENT_PC):
    #     raise PermissionDenied
    #
    # if request.method == 'GET':
    #     if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
    #         return render(request, 'clinicalcode/adminTemp/adminTemp.html', 
    #                       {'url': reverse('populate_collections_tags'),
    #                        'action_title': 'Split tags & collections'
    #                     })
    #
    # elif request.method == 'POST':
    #     if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
    #         code = request.POST.get('code')
    #         if code.strip() != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
    #             raise PermissionDenied
    #
    #         rowsAffected = {}
    #
    #
    #         ######################################################################
    #         # phenotype
    #         hisp = Phenotype.history.filter(id__gte=0)
    #         for hp in hisp:
    #             if hp.tags:
    #                 tag_ids_list = list(Tag.objects.filter(id__in=hp.tags, tag_type=1).values_list('id', flat=True))
    #                 collection_ids_list = list(Tag.objects.filter(id__in=hp.tags, tag_type=2).values_list('id', flat=True))
    #
    #                 hp.tags = tag_ids_list
    #                 hp.collections = collection_ids_list
    #                 hp.save()
    #
    #                 if hp.history_id == int(Phenotype.objects.get(pk=hp.id).history.latest().history_id):
    #                     p0 = Phenotype.objects.get(id=hp.id)
    #                     p0.tags = tag_ids_list
    #                     p0.collections = collection_ids_list
    #                     p0.save_without_historical_record()
    #
    #                     rowsAffected[hp.id] = "phenotype: " + hp.name + ":: tags/collections split"
    #
    #
    #
    #         ######################################################################
    #         # concepts
    #         hisc = Concept.history.filter(id__gte=0)
    #         for hc in hisc:
    #             if hc.tags:
    #                 tag_ids_list = list(Tag.objects.filter(id__in=hc.tags, tag_type=1).values_list('id', flat=True))
    #                 collection_ids_list = list(Tag.objects.filter(id__in=hc.tags, tag_type=2).values_list('id', flat=True))
    #
    #                 hc.tags = tag_ids_list
    #                 hc.collections = collection_ids_list
    #                 hc.save()
    #
    #                 if hc.history_id == int(Concept.objects.get(pk=hc.id).history.latest().history_id):
    #                     c0 = Concept.objects.get(id=hc.id)
    #                     c0.tags = tag_ids_list
    #                     c0.collections = collection_ids_list
    #                     c0.save_without_historical_record()
    #
    #                     rowsAffected[hc.id] = "concept: " + hc.name + ":: tags/collections split"
    #
    #
    #
    #
    #
    #         return render(request,
    #                     'clinicalcode/adminTemp/adminTemp.html',
    #                     {   'pk': -10,
    #                         'rowsAffected' : rowsAffected,
    #                         'action_title': 'Split tags & collections'
    #                     }
    #                     )
            
            
@login_required
def admin_delete_phenotypes(request):
    # for admin(developers) to mark phenotypes as deleted    
   
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not is_member(request.user, 'system developers'):
        raise PermissionDenied
    

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY: 
            return render(request, 'clinicalcode/adminTemp/admin_delete_phenotypes.html', 
                          {'url': reverse('admin_delete_phenotypes'),
                           'action_title': 'Delete Phenotypes'
                        })
    
    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY: 
            code = request.POST.get('code')
            if code.strip() != "6)r&9hpr_a0_4g(xan5p@=kaz2q_cd(v5n^!#ru*_(+d)#_0-i":
                raise PermissionDenied
    
            phenotype_ids = request.POST.get('phenotype_ids')
            phenotype_ids = phenotype_ids.strip().upper()
            
            ph_id_list = []
            if phenotype_ids:
                ph_id_list = [i.strip() for i in phenotype_ids.split(",")]
            
            rowsAffected = {}    
    
            if ph_id_list:
                for pk in ph_id_list:
                    pk = re.sub(' +', ' ', pk.strip())
                    id_match = re.search(r"(?i)^PH\d+$", pk)
                    if id_match:
                        if id_match.group() == id_match.string: # full match
                            is_valid_id, err, ret_id = db_utils.chk_valid_id(request, set_class=Phenotype, pk=pk, chk_permission=True)
                            if is_valid_id:
                                pk = str(ret_id)
                
                                if Phenotype.objects.filter(pk=pk).exists():
                                    phenotype = Phenotype.objects.get(pk=pk)
                                    phenotype.is_deleted = True
                                    phenotype.deleted = datetime.datetime.now()
                                    phenotype.deleted_by = request.user
                                    phenotype.updated_by = request.user
                                    phenotype.changeReason = "Deleted"
                                    phenotype.save()
                                    db_utils.modify_Entity_ChangeReason(Phenotype, pk, "Deleted")
                                    
                                    
                                    rowsAffected[pk] = "phenotype(" + str(pk) + "): \"" + phenotype.name + "\" is marked as deleted."
    
            else:
                rowsAffected[-1] = "Phenotype IDs NOT correct"
    
            return render(request,
                        'clinicalcode/adminTemp/admin_delete_phenotypes.html',
                        {   'pk': -10,
                            'rowsAffected' : rowsAffected,
                            'action_title': 'Delete Phenotypes'
                        }
                        )
            
            
@login_required
def admin_restore_phenotypes(request):
    # for admin(developers) to restore deleted phenotypes 
   
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not is_member(request.user, 'system developers'):
        raise PermissionDenied
    

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY: 
            return render(request, 'clinicalcode/adminTemp/admin_delete_phenotypes.html', 
                          {'url': reverse('admin_restore_phenotypes'),
                           'action_title': 'Restore Phenotypes'
                        })
    
    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY: 
            code = request.POST.get('code')
            if code.strip() != "6)r&9hpr_a0_4g(xan5p@=kaz2q_cd(v5n^!#ru*_(+d)#_0-i":
                raise PermissionDenied
    
            phenotype_ids = request.POST.get('phenotype_ids')
            phenotype_ids = phenotype_ids.strip().upper()

            ph_id_list = []
            if phenotype_ids:
                ph_id_list = [i.strip() for i in phenotype_ids.split(",")]
                
                            
            rowsAffected = {}    
    
            if ph_id_list:
                for pk in ph_id_list:
                    pk = re.sub(' +', ' ', pk.strip())
                    id_match = re.search(r"(?i)^PH\d+$", pk)
                    if id_match:
                        if id_match.group() == id_match.string: # full match
                            is_valid_id, err, ret_id = db_utils.chk_valid_id(request, set_class=Phenotype, pk=pk, chk_permission=True)
                            if is_valid_id:
                                pk = str(ret_id)
                                                    
                                if Phenotype.objects.filter(pk=pk).exists():
                                    phenotype = Phenotype.objects.get(pk=pk)
                                    phenotype.is_deleted = False
                                    phenotype.deleted = None
                                    phenotype.deleted_by = None
                                    phenotype.updated_by = request.user
                                    phenotype.changeReason = "Restored"
                                    phenotype.save()
                                    db_utils.modify_Entity_ChangeReason(Phenotype, pk, "Restored")
                                    
                                    rowsAffected[pk] = "phenotype(" + str(pk) + "): \"" + phenotype.name + "\" is restored."
    
            else:
                rowsAffected[-1] = "Phenotype IDs NOT correct"
    
            return render(request,
                        'clinicalcode/adminTemp/admin_delete_phenotypes.html',
                        {   'pk': -10,
                            'rowsAffected' : rowsAffected,
                            'action_title': 'Restore Phenotypes'
                        }
                        )
            


#### Dynamic Template  ####
            
@login_required
def admin_mig_phenotypes_dt(request):
    # for admin(developers) to migrate phenotypes into dynamic template
   
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not is_member(request.user, 'system developers'):
        raise PermissionDenied
    

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY: 
            return render(request, 'clinicalcode/adminTemp/admin_mig_phenotypes_dt.html', 
                          {'url': reverse('admin_mig_phenotypes_dt'),
                           'action_title': 'Migrate Phenotypes'
                        })
    
    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY: 
            code = request.POST.get('code')
            if code.strip() != "6)r&9hpr_a0_4g(xan5p@=kaz2q_cd(v5n^!#ru*_(+d)#_0-i":
                raise PermissionDenied
    
            phenotype_ids = request.POST.get('phenotype_ids')
            phenotype_ids = phenotype_ids.strip().upper()

            ph_id_list = []
            if phenotype_ids:
                if phenotype_ids == 'ALL':
                    ph_id_list = list(Phenotype.objects.all().values_list('id',  flat=True))
                else:
                    ph_id_list = [i.strip() for i in phenotype_ids.split(",")]
                
                            
            rowsAffected = {}    
    
            if ph_id_list:
                for pk in ph_id_list:
                    if phenotype_ids != 'ALL':
                        pk = re.sub(' +', ' ', pk.strip())
                        id_match = re.search(r"(?i)^PH\d+$", pk)
                        if id_match:
                            if id_match.group() == id_match.string: # full match
                                is_valid_id, err, ret_id = db_utils.chk_valid_id(request, set_class=Phenotype, pk=pk, chk_permission=True)
                                if is_valid_id:
                                    pk = str(ret_id)
                                                    
                    if Phenotype.objects.filter(pk=pk).exists():
                        phenotype = Phenotype.objects.get(pk=pk)
                        
                        ge = GenericEntity.objects.create(
                            id = phenotype.id,
                            name = phenotype.name,
                            author = phenotype.author,
                            
                            layout = LAYOUT_CLINICAL_CODED_PHENOTYPE,
                            status = ENTITY_STATUS_FINAL,

                            tags = phenotype.tags,
                            collections = phenotype.collections,  

                            description = phenotype.description,
                            implementation = phenotype.implementation,
                            validation = phenotype.validation,
                            publications = phenotype.publications,
                            citation_requirements = phenotype.citation_requirements,

                            template_id = Template.objects.get(pk=1),
                            template_data = [], # include type as ENUM
                            template_data2 = [],
                            
                            internal_comments = 'internal comments',
                            
                            created = phenotype.created, 
                            updated = phenotype.modified, 
                            created_by = phenotype.created_by, 
                            updated_by = phenotype.updated_by,
                            is_deleted = phenotype.is_deleted,
                            
                            deleted = phenotype.deleted, 
                            deleted_by = phenotype.deleted_by, 
                            owner = phenotype.owner,
                            group = phenotype.group,
                            
                            owner_access = phenotype.owner_access,
                            group_access = phenotype.group_access,
                            world_access = phenotype.world_access
                            )
                        ge.saveXX(entity = 'phenotype', serial_id = True, override_id = True)
        

    
                    #     db_utils.modify_Entity_ChangeReason(Phenotype, pk, "Restored")
                        
                        rowsAffected[pk] = "phenotype(" + str(pk) + "): \"" + phenotype.name + "\" is migrated."
    
            else:
                rowsAffected[-1] = "Phenotype IDs NOT correct"
    
            return render(request,
                        'clinicalcode/adminTemp/admin_mig_phenotypes_dt.html',
                        {   'pk': -10,
                            'rowsAffected' : rowsAffected,
                            'action_title': 'Migrate Phenotypes'
                        }
                        )
            

