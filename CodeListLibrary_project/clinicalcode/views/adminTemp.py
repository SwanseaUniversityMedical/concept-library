import time
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import \
    LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction  # , models, IntegrityError
from django.http import \
    HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
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

logger = logging.getLogger(__name__)

import json
import os

from django.core.exceptions import PermissionDenied
from django.db import connection, connections  # , transaction


@login_required
def api_remove_data(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            return render(request, 'clinicalcode/adminTemp/adminTemp.html', {})

    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            code = request.POST.get('code')
            if code.strip(
            ) != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
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

            rowsAffected[
                "**********************************"] = "**********************************"

            workingsets = WorkingSet.objects.filter(owner=request.user)
            for ws in workingsets:
                rowsAffected[ws.id] = "working set: " + ws.name + ":: deleted"
                ws.delete()

            workingsets = WorkingSet.history.filter(owner=request.user)
            for ws in workingsets:
                rowsAffected[ws.id] = "working set: " + ws.name + ":: deleted"
                ws.delete()

            rowsAffected[
                "**********************************"] = "**********************************"

            phenotypes = Phenotype.objects.filter(owner=request.user)
            for ph in phenotypes:
                rowsAffected[ph.id] = "phenotype: " + ph.name + ":: deleted"
                ph.delete()

            phenotypes = Phenotype.history.filter(owner=request.user)
            for ph in phenotypes:
                rowsAffected[ph.id] = "phenotype: " + ph.name + ":: deleted"
                ph.delete()

            rowsAffected[
                "**********************************"] = "**********************************"

            return render(request, 'clinicalcode/adminTemp/adminTemp.html', {
                'pk': -10,
                'strSQL': {},
                'rowsAffected': rowsAffected
            })


@login_required
def moveTags(request):
    # not needed any more
    raise PermissionDenied

    if not request.user.is_superuser:
        raise PermissionDenied

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            return render(request, 'clinicalcode/adminTemp/moveTags.html', {})

    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY:  # and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
            code = request.POST.get('code')
            if code.strip(
            ) != "nvd)#_0-i_a05n^5p6az2q_cd(_(+_4g)r&9h!#ru*pr(xa@=k":
                raise PermissionDenied

            rowsAffected = {}


#             ######################################################################
#             # move concept tags as attribute
#             distinct_concepts_with_tags = ConceptTagMap.objects.all().distinct('concept_id')
#             for dp in distinct_concepts_with_tags:
#                 #print "*************"
#                 #print dp.concept_id
#                 hisp = Concept.history.filter(id=dp.concept_id)
#                 for hp in hisp:
#                     #print hp.id, "...", hp.history_id
#                     concept_tags_history = db_utils.getHistoryTags(hp.id, hp.history_date)
#                     if concept_tags_history:
#                         concept_tag_list = [i['tag_id'] for i in concept_tags_history if 'tag_id' in i]
#                     else:
#                         concept_tag_list = []
#                     #print concept_tag_list
#                     with connection.cursor() as cursor:
#                         sql = """ UPDATE clinicalcode_historicalconcept
#                                     SET tags = '{""" + ','.join([str(i) for i in concept_tag_list]) + """}'
#                                     WHERE id="""+str(hp.id)+""" and history_id="""+str(hp.history_id)+""";
#                              """
#                         cursor.execute(sql)
#                         if hp.history_id == int(Concept.objects.get(pk=hp.id).history.latest().history_id):
#                             sql2 = """ UPDATE clinicalcode_concept
#                                     SET tags = '{""" + ','.join([str(i) for i in concept_tag_list]) + """}'
#                                     WHERE id="""+str(hp.id)+"""  ;
#                              """
#                             cursor.execute(sql2)
#
#                             rowsAffected[hp.id] = "concept: " + hp.name + ":: tags moved"
#
#
#
#
#
#             return render(request,
#                         'clinicalcode/adminTemp/moveTags.html',
#                         {   'pk': -10,
#                             'strSQL': {},
#                             'rowsAffected' : rowsAffected
#                         }
#                         )

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

    phenotypes = Phenotype.objects.all()
    for p in phenotypes:
        concept_id_list = [
            x['concept_id'] for x in json.loads(p.concept_informations)
        ]
        concept_hisoryid_list = [
            x['concept_version_id'] for x in json.loads(p.concept_informations)
        ]
        concepts = Concept.history.filter(id__in=concept_id_list,
                                          history_id__in=concept_hisoryid_list)

        for c in concepts:
            with connection.cursor() as cursor:
                sql = """ UPDATE clinicalcode_historicalconcept 
                            SET tags = '{""" + ','.join([
                    str(i) for i in p.tags
                ]) + """}'
                            WHERE id=""" + str(
                    c.id) + """ and history_id=""" + str(c.history_id) + """;
                    """
                cursor.execute(sql)
                sql2 = """ UPDATE clinicalcode_concept 
                            SET tags = '{""" + ','.join(
                    [str(i) for i in p.tags]) + """}'
                            WHERE id=""" + str(c.id) + """  ;
                    """
                cursor.execute(sql2)

                print(("phenotype/concept: " + p.name + "/" + c.name +
                       ":: tags moved"))


@login_required
def check_concepts_not_associated_with_phenotypes(request):

    phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(
        request, exclude_deleted=False)
    phenotypes_id = db_utils.get_list_of_visible_entity_ids(
        phenotypes, return_id_or_history_id="id")

    concepts_ids_in_phenotypes = []
    for p in phenotypes_id:
        phenotype = Phenotype.objects.get(pk=p)
        concept_id_list = [
            x['concept_id'] for x in json.loads(phenotype.concept_informations)
        ]

        concepts_ids_in_phenotypes = concepts_ids_in_phenotypes + concept_id_list

    concepts_ids_in_phenotypes = set(concepts_ids_in_phenotypes)

    concepts = db_utils.get_visible_live_or_published_concept_versions(
        request, exclude_deleted=False)

    all_concepts_ids = db_utils.get_list_of_visible_entity_ids(
        concepts, return_id_or_history_id="id")

    result = all(elem in concepts_ids_in_phenotypes
                 for elem in all_concepts_ids)
    if result:
        messages.success(request,
                         "Yes, all concepts are associated with phenotypes.")
    else:
        messages.warning(
            request, "No, NOT all concepts are associated with phenotypes.")

    unasscoiated_concepts_ids = list(
        set(all_concepts_ids) - set(concepts_ids_in_phenotypes))

    unasscoiated_concepts = Concept.objects.filter(
        id__in=unasscoiated_concepts_ids).order_by('id')

    return render(request,
                  'clinicalcode/adminTemp/concepts_not_in_phenotypes.html', {
                      'count': unasscoiated_concepts.count(),
                      'concepts': unasscoiated_concepts
                  })
