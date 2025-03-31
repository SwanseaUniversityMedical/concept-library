from datetime import datetime
from operator import is_not
from functools import partial
from django.db import connection
from django.conf import settings
from django.urls import reverse
from django.db.models import Q
from django.shortcuts import render
from django.utils.timezone import make_aware
from rest_framework.reverse import reverse
from django.core.exceptions import BadRequest, PermissionDenied
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required

import re
import json
import logging
import dateutil

from clinicalcode.entity_utils import permission_utils, gen_utils

from clinicalcode.models.Tag import Tag
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Concept import Concept
from clinicalcode.models.Template import Template
from clinicalcode.models.Phenotype import Phenotype
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedPhenotype import PublishedPhenotype
from clinicalcode.models.Organisation import Organisation, OrganisationMembership

from clinicalcode.models.HDRNSite import HDRNSite
from clinicalcode.models.HDRNDataAsset import HDRNDataAsset
from clinicalcode.models.HDRNDataCategory import HDRNDataCategory

logger = logging.getLogger(__name__)

####       Const       ####
BASE_LINKAGE_TEMPLATE = {
    # all sex is '3' unless specified by user
    'sex': '3',
    # all PhenotypeType is 'Disease or syndrome' unless specified by user
    'type': '2',
    # all version is '1' for migration
    'version': '1',
}

#### Dynamic Template  ####
def try_parse_hdrn_datetime(obj, default=None):
    if not isinstance(obj, dict):
        return default

    typed = obj.get('type')
    value = obj.get('value')
    if typed != 'datetime' or not isinstance(value, str) or gen_utils.is_empty_string(value):
        return default

    try:
        result = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
    except:
        return default
    else:
        return make_aware(result)

def sort_pk_list(a, b):
    pk1 = int(a.replace('PH', ''))
    pk2 = int(b.replace('PH', ''))

    if pk1 > pk2:
        return 1
    elif pk1 < pk2:
        return -1
    return 0

def try_parse_doi(publications):
    pattern = re.compile(r'\b(10[.][0-9]{4,}(?:[.][0-9]+)*\/(?:(?![\"&\'<>])\S)+)\b')

    output = [ ]
    for publication in publications:
        if publication is None or len(str(publication).strip()) < 1:
            continue

        doi = pattern.findall(publication)
        output.append({
            'details': publication,
            'doi': doi[0] if len(doi) > 0 else None
        })
    
    return output

def compute_related_brands(pheno, default=''):
    collections = pheno.collections
    if not isinstance(collections, list):
        return default
    
    related_brands = set([])
    for collection_ids in collections:
        collection = Tag.objects.filter(id=collection_ids)
        if not collection.exists():
            continue

        brand = collection.first().collection_brand
        if brand is None:
            continue
        related_brands.add(brand.id)
    
    related_brands = ','.join([str(x) for x in list(related_brands)])
    return "brands='{%s}' " % related_brands

def get_publications(concept):
    publication_doi = concept.publication_doi
    publication_link = concept.publication_link

    has_publication = not gen_utils.is_empty_string(publication_link)
    has_publication_doi = not gen_utils.is_empty_string(publication_doi)
    
    if has_publication:
        return [{
            'details': publication_link,
            'doi': None if not has_publication_doi else publication_doi
        }]

    return None

def get_null_on_empty(value):
    if not gen_utils.is_empty_string(value):
        return value
    return None

def get_transformed_data(concept, template):
    metadata = {
        'name': concept.name,
        'author': concept.author,
        'definition': get_null_on_empty(concept.description),
        'validation': get_null_on_empty(concept.validation_description),
        'citation_requirements': get_null_on_empty(concept.citation_requirements),
        'publications': get_publications(concept),
        'tags': concept.tags,
        'collections': concept.collections,
        'owner': concept.owner,
        'group': concept.group,
        'owner_access': concept.owner_access,
        'group_access': concept.group_access,
        'template': template,

        # maintain created / updated status
        'created': concept.created,
        'created_by': concept.created_by,
        'updated': make_aware(datetime.now()),
        'updated_by': concept.modified_by,

        # maintain archived status
        'is_deleted': concept.is_deleted,
        'deleted': concept.deleted,
        'deleted_by': concept.deleted_by,

        # unpublished & no access
        'status': 1,
        'world_access': 1,
    }

    if concept.is_deleted:
        metadata.update({ 'internal_comments': 'Legacy Concept archived by user on legacy site' })

    template_data = {
        'agreement_date': concept.entry_date.strftime('%Y-%m-%d'),
        'source_reference': get_null_on_empty(concept.source_reference),
        'coding_system': [concept.coding_system.id] if concept.coding_system else None,
        'concept_information': [
            { 'concept_id': concept.id, 'concept_version_id': concept.history_id }
        ],
    } | BASE_LINKAGE_TEMPLATE

    metadata.update({
        'template_data': template_data,
        'template_version': 1,
    })

    return metadata

@login_required
def admin_fix_malformed_codes(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_fix_malformed_codes'),
                'action_title': 'Strip Concept Codes',
                'hide_phenotype_options': True,
            }
        )
    
    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')
    
    with connection.cursor() as cursor:
        sql = '''
        update public.clinicalcode_code
           set code = 
                 regexp_replace(
                   code, 
                   '^[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+|[\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]|[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+$', 
                   ''
                 );

        update public.clinicalcode_historicalcode
           set code = 
                 regexp_replace(
                   code, 
                   '^[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+|[\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]|[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+$', 
                   ''
                 );

        update public.clinicalcode_conceptcodeattribute
           set code = 
                 regexp_replace(
                   code, 
                   '^[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+|[\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]|[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+$', 
                   ''
                 );

        update public.clinicalcode_historicalconceptcodeattribute
           set code = 
                 regexp_replace(
                   code, 
                   '^[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+|[\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]|[\s\u00a0\u180e\u2007\u200b-\u200f\u202f\u2060\ufeff]+$', 
                   ''
                 );
        '''
        cursor.execute(sql)

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Strip Concept Codes',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_fix_concept_linkage(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_fix_concept_linkage'),
                'action_title': 'Fix Concept Linkage',
                'hide_phenotype_options': True,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    row_count = 0
    with connection.cursor() as cursor:

        ''' Update from legacy reference first ... '''
        sql = '''

        with
          legacy_reference as (
            select phenotype.id as phenotype_id,
                   concept->>'concept_id' as concept_id,
                   concept->>'concept_version_id' as concept_version_id,
                   created
              from public.clinicalcode_phenotype as phenotype,
                   json_array_elements(phenotype.concept_informations::json) as concept
          ),
          ranked_legacy_concepts as (
            select phenotype_id,
                   cast(concept_id as integer) as concept_id,
                   cast(concept_version_id as integer) as concept_version_id,
                   rank() over (
                     partition by phenotype_id
                         order by created asc
                   ) as ranking
              from legacy_reference
          )

        update public.clinicalcode_historicalconcept as trg
           set phenotype_owner_id = src.phenotype_id
          from (
            select *
              from ranked_legacy_concepts
             where ranking = 1
          ) as src
         where trg.id = src.concept_id
           and trg.phenotype_owner_id is null;

        '''

        cursor.execute(sql)
        row_count += cursor.rowcount

        ''' ... then update from current reference '''
        sql = '''

        with
          entity_reference as (
            select id as phenotype_id,
                   history_id as phenotype_version_id,
                   cast(concepts->>'concept_id' as integer) as concept_id,
                   cast(concepts->>'concept_version_id' as integer) as concept_version_id
              from (
                select id,
                       history_id,
                       concepts
                  from public.clinicalcode_historicalgenericentity as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                 where template_id = 1
                   and json_array_length(entity.template_data::json->'concept_information') > 0
              ) hge_concepts
          ),
          first_child_concept as (
            select concept_id as concept_id,
                   min(concept_version_id) as concept_version_id
              from entity_reference as entity
             group by concept_id
          ),
          earliest_entity as (
            select phenotype_id,
                   concept_id,
                   concept_version_id
              from (
                select phenotype_id,
                      rank() over (
                        partition by phenotype_id
                            order by phenotype_version_id asc
                      ) as ranking,
                      concept.concept_id,
                      concept.concept_version_id
                  from entity_reference as entity
                  join first_child_concept as concept
                    using (concept_id, concept_version_id)
              ) as hci
             where ranking = 1
          )

        update public.clinicalcode_historicalconcept as trg
           set phenotype_owner_id = src.phenotype_id
          from earliest_entity as src
         where trg.id = src.concept_id
           and trg.phenotype_owner_id is null;

        '''

        cursor.execute(sql)
        row_count += cursor.rowcount

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': f'Updated {str(row_count)} entities' },
            'action_title': 'Fix Concept Linkage',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_fix_coding_system_linkage(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_fix_coding_system_linkage'),
                'action_title': 'Fix Coding System Linkage',
                'hide_phenotype_options': True,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    row_count = 0
    with connection.cursor() as cursor:
        sql = '''

        update public.clinicalcode_historicalgenericentity as trg
           set template_data['coding_system'] = to_jsonb(src.coding_system)
          from (
            select entity.phenotype_id,
                   entity.phenotype_version_id,
                   array_agg(distinct concept.coding_system_id::integer) as coding_system
              from public.clinicalcode_historicalconcept as concept
              join (
                select id as phenotype_id,
                       history_id as phenotype_version_id,
                       cast(concepts->>'concept_id' as integer) as concept_id,
                       cast(concepts->>'concept_version_id' as integer) as concept_version_id
                  from (
                    select id,
                           history_id,
                           concepts
                      from public.clinicalcode_historicalgenericentity as entity,
                           json_array_elements(entity.template_data::json->'concept_information') as concepts
                     where template_id = 1
                       and json_array_length(entity.template_data::json->'concept_information') > 0
                  ) results
              ) as entity
            on entity.concept_id = concept.id
               and entity.concept_version_id = concept.history_id
            group by entity.phenotype_id,
                     entity.phenotype_version_id
          ) src
        where trg.id = src.phenotype_id
          and trg.history_id = src.phenotype_version_id
          and trg.template_id = 1
          and array(
            select jsonb_array_elements_text(trg.template_data->'coding_system')
          )::int[] <> src.coding_system;

        '''

        cursor.execute(sql)
        row_count = cursor.rowcount

        sql = '''

        update public.clinicalcode_genericentity as trg
           set template_data['coding_system'] = to_jsonb(src.coding_system)
          from (
            select entity.phenotype_id,
                   array_agg(distinct concept.coding_system_id::integer) as coding_system
              from public.clinicalcode_historicalconcept as concept
              join (
                select id as phenotype_id,
                       cast(concepts->>'concept_id' as integer) as concept_id,
                       cast(concepts->>'concept_version_id' as integer) as concept_version_id
                  from (
                    select id,
                           concepts
                      from public.clinicalcode_genericentity as entity,
                           json_array_elements(entity.template_data::json->'concept_information') as concepts
                     where template_id = 1
                       and json_array_length(entity.template_data::json->'concept_information') > 0
                  ) results
              ) as entity
            on entity.concept_id = concept.id
               and entity.concept_version_id = concept.history_id
            group by entity.phenotype_id
          ) src
        where trg.id = src.phenotype_id
          and trg.template_id = 1
          and array(
            select jsonb_array_elements_text(trg.template_data->'coding_system')
          )::int[] <> src.coding_system;

        '''

        cursor.execute(sql)
        row_count += cursor.rowcount

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': f'Updated {str(row_count)} entities' },
            'action_title': 'Fix Coding System Linkage',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_force_adp_linkage(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_force_adp_links'),
                'action_title': 'Force ADP linkage',
                'hide_phenotype_options': True,
            }
        )
    
    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')
    
    adp = Group.objects.get(name='ADP')

    phenotypes = GenericEntity.objects.exclude(Q(collections__isnull=True) | Q(collections__len__lte=0))
    for phenotype in phenotypes:
        collections = phenotype.collections
        if not isinstance(collections, list):
            continue

        related_brands = set([])
        for collection_id in collections:
            collection = Tag.objects.filter(id=collection_id)
            if not collection.exists():
                continue
            
            brand = collection.first().collection_brand
            if brand is None:
                continue
            related_brands.add(brand.id)
        
        if 1 not in related_brands:
            continue

        phenotype.brands = list(related_brands)
        phenotype.group = adp
        phenotype.save_without_historical_record()

    with connection.cursor() as cursor:
        sql = '''
        update public.clinicalcode_historicalgenericentity entity
           set
               group_id = selected.group_id,
               brands = selected.brands
          from public.clinicalcode_genericentity selected
         where entity.id = selected.id
           and 1 = any(selected.brands);
        '''
        cursor.execute(sql)

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Force ADP linkage',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_force_brand_links(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_force_brand_links'),
                'action_title': 'Force brand linkage',
                'hide_phenotype_options': True,
            }
        )
    
    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    phenotypes = GenericEntity.objects.filter(Q(brands__isnull=True) | Q(brands__len__lte=0)) \
        .exclude(Q(collections__isnull=True) | Q(collections__len__lte=0))
    
    for phenotype in phenotypes:        
        collections = phenotype.collections
        if not isinstance(collections, list):
            continue

        related_brands = set([])
        for collection_id in collections:
            collection = Tag.objects.filter(id=collection_id)
            if not collection.exists():
                continue
            
            brand = collection.first().collection_brand
            if brand is None:
                continue
            related_brands.add(brand.id)

        phenotype.brands = list(related_brands)
        phenotype.save_without_historical_record()

    # save historical
    phenotypes = GenericEntity.history.filter(Q(brands__isnull=True) | Q(brands__len__lte=0)) \
        .exclude(Q(collections__isnull=True) | Q(collections__len__lte=0))
    
    for phenotype in phenotypes:        
        collections = phenotype.collections
        if not isinstance(collections, list):
            continue

        related_brands = set([])
        for collection_id in collections:
            collection = Tag.objects.filter(id=collection_id)
            if not collection.exists():
                continue
            
            brand = collection.first().collection_brand
            if brand is None:
                continue
            related_brands.add(brand.id)
        
        related_brands = list(related_brands)
        with connection.cursor() as cursor:
            sql = '''
                UPDATE public.clinicalcode_historicalgenericentity
                   SET brands = %(brands)s
                 WHERE id = %(phenotype_id)s
                   AND history_id = %(history_id)s
            '''
            cursor.execute(
                sql, 
                { 'brands': related_brands, 'phenotype_id': phenotype.id, 'history_id': phenotype.history_id }
            )

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Force brand linkage',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_update_phenoflowids(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_update_phenoflowids'),
                'action_title': 'Update phenoflow ids',
                'hide_phenotype_options': False,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    try:
        input_data = request.POST.get('input_data')
        input_data = json.loads(input_data)
    except:
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html',
            {
                'pk': -10,
                'errorMsg': { 'message': 'Unable to read data provided' },
                'action_title': 'Update phenoflow ids',
                'hide_phenotype_options': True,
            }
        )
    
    with connection.cursor() as cursor:
        sql = f'''
        update public.clinicalcode_genericentity as trg
           set template_data['phenoflowid'] = to_jsonb(src.phenoflowid)
          from (
            select *
            from jsonb_to_recordset(
                '{json.dumps(input_data)}'::jsonb
            ) as x(id varchar, phenoflowid varchar)
          ) as src
         where trg.id = src.id
           and trg.template_id = 1;
        '''
        cursor.execute(sql)
        entity_updates = cursor.rowcount

        sql = f'''
        update public.clinicalcode_historicalgenericentity as trg
           set template_data['phenoflowid'] = to_jsonb(src.phenoflowid)
          from (
            select *
            from jsonb_to_recordset(
                '{json.dumps(input_data)}'::jsonb
            ) as x(id varchar, phenoflowid varchar)
          ) as src
         where trg.id = src.id
           and trg.template_id = 1;
        '''
        cursor.execute(sql)
        historical_updates = cursor.rowcount
    
    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { 
                '1': f'entities: {entity_updates}, historical: {historical_updates}' 
            },
            'action_title': 'Update phenoflow ids',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_upload_hdrn_assets(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied

    if not request.user.is_superuser:
        raise PermissionDenied

    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_upload_hdrn_assets'),
                'action_title': 'Upload HDRN Assets',
                'hide_phenotype_options': False,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    try:
        input_data = request.POST.get('input_data')
        input_data = json.loads(input_data)
    except:
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html',
            {
                'pk': -10,
                'errorMsg': { 'message': 'Unable to read data provided' },
                'action_title': 'Upload HDRN Assets',
                'hide_phenotype_options': True,
            }
        )

    brand = Brand.objects.filter(name__iexact='HDRN')
    if brand.exists():
        brand = brand.first()
    else:
        brand = Brand.objects.create(
                name='HDRN',
                description='Health Data Research Network Canada (HDRN Canada) is a pan-Canadian network of member '
                            'organizations that either hold linkable health and health-related data for entire populations '
                            'and/or have mandates and roles relating directly to access or use of those data. ',
                website='https://www.hdrn.ca',
                logo_path='img/brands/HDRN/',
                index_path='clinicalcode/index.html',
                footer_images=[
                    {"url": "https://www.hdrn.ca", "brand": "HDRN",
                     "image_src": "img/Footer_logos/HDRN_logo.png"},
                    {"url": "https://conceptlibrary.saildatabank.com/", "brand": "Concept Library",
                     "image_src": "img/Footer_logos/concept_library_on_white.png"},
                    {"url": "http://saildatabank.com", "brand": "SAIL Databank ",
                     "image_src": "img/Footer_logos/SAIL_alt_logo_on_white.png"}
                ],
                overrides={"stats_context": "^(?!/HDRN)", "content_visibility": {"allow_null": True, "allowed_brands": [1, 2, 3]}}
        )

    models = {}
    metadata = input_data.get('metadata')
    for key, data in metadata.items():
        result = None
        match key:
            case 'site':
                '''HDRNSite'''
                result = HDRNSite.objects.bulk_create([HDRNSite(name=v) for v in data])
            case 'categories':
                '''HDRNDataCategory'''
                result = HDRNDataCategory.objects.bulk_create([HDRNDataCategory(name=v) for v in data])
            case 'data_categories':
                '''Tag (tag_type=1)'''
                result = Tag.objects.bulk_create([Tag(description=v, tag_type=1, collection_brand=brand) for v in data])
            case _:
                pass

        if result is not None:
            models.update({ key: result })

    now = make_aware(datetime.now())
    assets = input_data.get('assets')
    to_create = []

    for data in assets:
        site = data.get('site')
        cats = data.get('data_categories')

        if isinstance(cats, list):
            cats = [models.get('data_categories')[v - 1].id for v in cats if models.get('data_categories')[v - 1] is not None]

        site = next((x for x in models.get('site') if x.id == site), None) if isinstance(site, int) else None
        created_date = try_parse_hdrn_datetime(data.get('created_date', None), default=now)
        modified_date = try_parse_hdrn_datetime(data.get('modified_date', None), default=now)

        to_create.append(HDRNDataAsset(
            name=data.get('name'),
            description=data.get('description'),
            hdrn_id=data.get('hdrn_id'),
            hdrn_uuid=data.get('hdrn_uuid'),
            site=site,
            link=data.get('link'),
            years=data.get('years'),
            scope=data.get('scope'),
            region=data.get('region'),
            purpose=data.get('purpose'),
            collection_period=data.get('collection_period'),
            data_level=data.get('data_level'),
            data_categories=cats,
            created=created_date,
            modified=modified_date
        ))

    models.update({ 'assets': HDRNDataAsset.objects.bulk_create(to_create) })

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { k: len(v) for k, v in models.items() },
            'action_title': 'Upload HDRN Assets',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_update_phenoflow_targets(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied

    if not request.user.is_superuser:
        raise PermissionDenied

    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_update_phenoflow_targets'),
                'action_title': 'Update Phenoflow Targets',
                'hide_phenotype_options': False,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    try:
        input_data = request.POST.get('input_data')
        input_data = json.loads(input_data)
    except:
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html',
            {
                'pk': -10,
                'errorMsg': { 'message': 'Unable to read data provided' },
                'action_title': 'Update Phenoflow Targets',
                'hide_phenotype_options': True,
            }
        )

    with connection.cursor() as cursor:
        sql = f'''
        update public.clinicalcode_genericentity as trg
           set template_data['phenoflowid'] = to_jsonb(src.target)
          from (
            select *
            from jsonb_to_recordset(
                '{json.dumps(input_data)}'::jsonb
            ) as x(id varchar, source int, target varchar)
          ) as src
         where trg.id = src.id
           and trg.template_data::jsonb ? 'phenoflowid';
        '''
        cursor.execute(sql)
        entity_updates = cursor.rowcount

        sql = f'''
        update public.clinicalcode_historicalgenericentity as trg
           set template_data['phenoflowid'] = to_jsonb(src.target)
          from (
            select *
            from jsonb_to_recordset(
                '{json.dumps(input_data)}'::jsonb
            ) as x(id varchar, source int, target varchar)
          ) as src
         where trg.id = src.id
           and trg.template_data::jsonb ? 'phenoflowid';
        '''
        cursor.execute(sql)
        historical_updates = cursor.rowcount

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { 
                '1': f'entities: {entity_updates}, historical: {historical_updates}' 
            },
            'action_title': 'Update Phenoflow Targets',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_force_concept_linkage_dt(request):
    """
        Bulk updates unlinked Concepts such that they have a phenotype owner by creating
        a pseudo-Phenotype using the metadata found within the legacy Conept

        i.e.
            1. Find unlinked Concepts, e.g. Concept<phenotype_owner=null>
            2. For each unlinked Concept, create a pseudo-Phenotype using its metadata
            3. Update the unlinked Concept such that it's phenotype_owner field relates to
               the newly created pseudo-Phenotype

    """
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_force_links_dt'),
                'action_title': 'Force Concept Linkage',
                'hide_phenotype_options': True,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    unlinked_concepts = Concept.objects.filter(phenotype_owner__isnull=True)
    unlinked_concepts = list(unlinked_concepts.values_list('id', flat=True))
    unlinked_concepts = Concept.history.filter(
        id__in=unlinked_concepts
    ) \
        .order_by('id', '-history_id') \
        .distinct('id')

    template = Template.objects.get(id=1)

    bulk_concepts = [ ]
    for concept in unlinked_concepts:
        data = get_transformed_data(concept, template)
        entity = GenericEntity.objects.create(**data)

        instance = concept.instance
        instance.phenotype_owner = entity
        bulk_concepts.append(instance)

    if len(bulk_concepts) > 0:
        Concept.objects.bulk_update(bulk_concepts, ['phenotype_owner'])

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Force Concept Linkage',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_fix_read_codes_dt(request):
    """
        Fix data quality issues associated with Read Codes V2 table's reliance
        on the 30char field

        Achieves this by:
            1. Coalescing the pref_term field (30, 60 and 198 char) and updating its 'description' field
            2. Setting the Coding System's desc column to 'description'

    """
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_fix_read_codes_dt'),
                'action_title': 'Fix Read Codes',
                'hide_phenotype_options': True,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    with connection.cursor() as cursor:
        sql = '''
        -- readcodesv2
        update public.clinicalcode_read_cd_cv2_scd as trg
           set description = coalesce(trg.pref_term_198, coalesce(trg.pref_term_60, trg.pref_term_30))
         where trg.description is null;

        -- readcodes v3
        update public.clinicalcode_read_cd_cv3_terms_scd as trg
           set description = coalesce(trg.term_198, coalesce(trg.term_60, trg.term_30))
         where trg.description is null;

        -- update coding systems
        update public.clinicalcode_codingsystem
           set desc_column_name = 'description'
         where name ilike 'read codes%';
        '''
        cursor.execute(sql)

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Fix Read Codes',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_mig_concepts_dt(request):
    """
        Approximates ownership of a Concept given it's first appearance
        in a phenotype

        i.e.
            for concept in concepts:
                concept.phenotype_owner = earliest_record_as_child_of_phenotype(concept.id)

    """
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_mig_concepts_dt'),
                'action_title': 'Migrate Concepts',
                'hide_phenotype_options': True,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    with connection.cursor() as cursor:
        sql = '''
        with
            split_concepts as (
                select phenotype.id as phenotype_id, 
                    concept ->> 'concept_id' as concept_id,
                    created
                from public.clinicalcode_phenotype as phenotype,
                    json_array_elements(phenotype.concept_informations :: json) as concept
            ),
            ranked_concepts as (
                select phenotype_id, concept_id,
                    rank() over(
                        partition by concept_id
                        order by created
                    ) ranking
                from split_concepts
            )

        update public.clinicalcode_concept as trg
           set phenotype_owner_id = src.phenotype_id
          from (
            select distinct on (concept_id) *
              from ranked_concepts
          ) src
         where (trg.is_deleted is null or trg.is_deleted = false)
           and trg.id = src.concept_id::int;
        '''
        cursor.execute(sql)

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Migrate Concepts',
            'hide_phenotype_options': True,
        }
    )

@login_required
def admin_mig_phenotypes_dt(request):
    # for admin(developers) to migrate phenotypes into dynamic template
   
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    if request.method == 'GET':
        if not settings.CLL_READ_ONLY: 
            return render(request, 'clinicalcode/adminTemp/admin_temp_tool.html', 
                          {'url': reverse('admin_mig_phenotypes_dt'),
                           'action_title': 'Migrate Phenotypes'
                        })
    
    elif request.method == 'POST':
        if not settings.CLL_READ_ONLY: 
            phenotype_ids = request.POST.get('phenotype_ids')
            phenotype_ids = phenotype_ids.strip().upper()

            rowsAffected = {} 
            
            if phenotype_ids:
                if phenotype_ids == 'ALL': # mig ALL                    
                    with connection.cursor() as cursor:
                        sql = "truncate table clinicalcode_historicalgenericentity restart identity; "
                        cursor.execute(sql)
                        sql2 = "truncate table clinicalcode_historicalpublishedgenericentity restart identity; "
                        cursor.execute(sql2)   
                        sql3 = """
                        DO
                        $do$
                        declare CONSTRAINT_NAME text:= (
                            select quote_ident(conname)
                            from pg_constraint
                            where conrelid = 'public.clinicalcode_concept'::regclass
                            and confrelid = 'public.clinicalcode_genericentity'::regclass
                            limit 1
                        );

                        begin
                            execute 'alter table public.clinicalcode_concept drop constraint if exists ' || CONSTRAINT_NAME;

                            execute 'update public.clinicalcode_concept set phenotype_owner_id = NULL';

                            execute 'truncate table public.clinicalcode_genericentity, public.clinicalcode_publishedgenericentity restart identity';

                            execute 'alter table public.clinicalcode_concept
                                add constraint ' || CONSTRAINT_NAME || ' foreign key (phenotype_owner_id)
                                references public.clinicalcode_genericentity (id)';
                        end
                        $do$
                        """
                        cursor.execute(sql3)
                    
                    
                        mig_h_pheno = """
                        INSERT INTO clinicalcode_historicalgenericentity(
                            id, name, author, status, tags, collections, definition
                            , implementation, validation, citation_requirements
                            , template_data, template_id, template_version, internal_comments
                            , created, updated, is_deleted, deleted, owner_access, group_access, world_access
                            , history_id, history_date, history_change_reason, history_type, history_user_id
                            , created_by_id, deleted_by_id, group_id, owner_id, updated_by_id
                            )
                        SELECT id, name, author, 2 status, tags, collections, description definition
                            , implementation, validation, citation_requirements
                            , '{}' template_data, 1 template_id, 1 template_version, '' internal_comments
                            , created, modified updated, is_deleted, deleted, owner_access, group_access, world_access
                            , history_id, history_date, history_change_reason, history_type, history_user_id
                            , created_by_id, deleted_by_id, group_id, owner_id, updated_by_id
                        FROM clinicalcode_historicalphenotype;
                        """
                        cursor.execute(mig_h_pheno) 
                    
                        mig_pheno = """
                        INSERT INTO clinicalcode_genericentity(
                            id, name, author, status, tags, collections, definition
                            , implementation, validation, citation_requirements
                            , template_data, template_id, template_version, internal_comments
                            , created, updated, is_deleted, deleted, owner_access, group_access, world_access
                            , created_by_id, deleted_by_id, group_id, owner_id, updated_by_id
                            )
                        SELECT id, name, author, 2 status, tags, collections, description definition                       
                            , implementation, validation, citation_requirements
                            , '{}' template_data, 1 template_id, 1 template_version, '' internal_comments
                            , created, modified updated, is_deleted, deleted, owner_access, group_access, world_access
                            , created_by_id, deleted_by_id, group_id, owner_id, updated_by_id
                        FROM clinicalcode_phenotype;
                        """
                        cursor.execute(mig_pheno)
                    
                        mig_h_published_records = """
                        insert into clinicalcode_historicalpublishedgenericentity(
                            id, entity_id, entity_history_id, code_count
                            , moderator_id, approval_status
                            , created, created_by_id, modified, modified_by_id
                            , history_id, history_date, history_change_reason, history_type, history_user_id
                            )    
                        SELECT id, phenotype_id, phenotype_history_id, null code_count
                            , moderator_id, approval_status
                            , created, created_by_id, modified, modified_by_id
                            , history_id, history_date, history_change_reason, history_type, history_user_id
                            FROM clinicalcode_historicalpublishedphenotype
                            where phenotype_id like 'PH%';
                        """
                        cursor.execute(mig_h_published_records)
                    
                        mig_published_records = """
                        insert into clinicalcode_publishedgenericentity(
                            id, entity_id, entity_history_id, code_count
                            , moderator_id, approval_status
                            , created, created_by_id, modified, modified_by_id
                            )    
                        SELECT id, phenotype_id, phenotype_history_id, null code_count
                            , moderator_id, approval_status
                            , created, created_by_id, modified, modified_by_id
                            FROM clinicalcode_publishedphenotype
                            where phenotype_id like 'PH%';
                        """
                        cursor.execute(mig_published_records)                           
                    
                    ######################################
                    live_pheno = Phenotype.objects.all()

                    live_pheno_count = Phenotype.objects.extra(
                        select={
                            'true_id': '''CAST(SUBSTRING(id, 3, LENGTH(id)) AS INTEGER)'''
                        }
                    ).order_by('-true_id', 'id').first()
                    live_pheno_count = live_pheno_count.true_id

                    for p in live_pheno:
                        temp_data = get_custom_fields_key_value(p)
                        temp_data['version'] = 1
                        publication_items = try_parse_doi([i.replace("'", "''") for i in p.publications])
                        
                        ''' update publish status in live generic entity '''
                        publish_status_str = ""
                        approval_status = ""
                        p_latest_history_id =  p.history.latest().history_id
                        if PublishedPhenotype.objects.filter(phenotype_id=p.id, phenotype_history_id=p_latest_history_id).exists():
                            approval_status = str(PublishedPhenotype.objects.get(phenotype_id=p.id, phenotype_history_id=p_latest_history_id).approval_status)
                            publish_status_str = " , publish_status = " + approval_status + " "
                        
                        upd_t = p.modified
                        if not upd_t:
                            upd_t = make_aware(datetime.now())
                        upd_t = upd_t.strftime('%Y-%m-%d %H:%M:%S')

                        brand_status = compute_related_brands(p)
                        with connection.cursor() as cursor:
                            sql_p = """
                                    update clinicalcode_genericentity  
                                    set updated = '"""+upd_t+"""',
                                        template_data = '"""+json.dumps(temp_data)+"""',
                                        publications= '"""+json.dumps(publication_items)+"""'
                                        """+publish_status_str+"""
                                        , """+brand_status+"""
                                    where id ='"""+p.id+"""' ;
                                    """
                            cursor.execute(sql_p)

                            sql_p = """
                                    update clinicalcode_historicalgenericentity  
                                    set """+brand_status+"""
                                    where id ='"""+p.id+"""';
                                    """
                            cursor.execute(sql_p)
                    
                    with connection.cursor() as cursor:
                        sql_entity_count = "update clinicalcode_entityclass set entity_count ="+str(live_pheno_count)+" where id = 1;"
                        cursor.execute(sql_entity_count)

                    historical_pheno = Phenotype.history.filter(~Q(id='x'))
                    for p in historical_pheno:
                        temp_data = get_custom_fields_key_value(p)
                        temp_data['version'] = 1
                        publication_items = try_parse_doi([i.replace("'", "''") for i in p.publications])
                        with connection.cursor() as cursor:
                            sql_p = """ update  clinicalcode_historicalgenericentity  
                                    set template_data = '"""+json.dumps(temp_data)+"""'
                                        , publications= '"""+json.dumps(publication_items)+"""'
                                    where id ='"""+p.id+"""' and history_id='"""+str(p.history_id)+"""';
                                    """
                            cursor.execute(sql_p)
                            
                    ''' update publish status in historical generic entity '''
                    with connection.cursor() as cursor:
                        sql_publish_status = """
                                                UPDATE public.clinicalcode_historicalgenericentity AS hg
                                                SET publish_status = p.approval_status
                                                FROM public.clinicalcode_publishedgenericentity AS p
                                                WHERE hg.id = p.entity_id and hg.history_id = p.entity_history_id ;

                                                UPDATE public.clinicalcode_historicalgenericentity AS hg
                                                SET publish_status = p.approval_status
                                                FROM public.clinicalcode_publishedgenericentity AS p
                                                WHERE hg.id = p.entity_id and hg.history_id = p.entity_history_id ;
                                            """
                        cursor.execute(sql_publish_status)
                        

                    with connection.cursor() as cursor:
                        cursor.execute("""SELECT SETVAL(
                            pg_get_serial_sequence('clinicalcode_historicalgenericentity', 'history_id'),
                            (SELECT MAX(history_id) FROM public.clinicalcode_historicalgenericentity)
                        );""")
                        
                    with connection.cursor() as cursor:
                        cursor.execute("""SELECT SETVAL(
                            pg_get_serial_sequence('clinicalcode_historicalpublishedgenericentity', 'history_id'),
                            (SELECT MAX(history_id) FROM public.clinicalcode_historicalpublishedgenericentity)
                        );""")

                    with connection.cursor() as cursor:
                        cursor.execute("""SELECT setval('clinicalcode_publishedgenericentity_id_seq',
                                       (SELECT MAX(id) FROM public.clinicalcode_publishedgenericentity)+1);""")


                    ######################################
                    rowsAffected[1] = "phenotypes migrated."
            else:
                rowsAffected[-1] = "Phenotype IDs NOT correct"
    
            return render(
                request,
                'clinicalcode/adminTemp/admin_temp_tool.html',
                {   'pk': -10,
                    'rowsAffected' : rowsAffected,
                    'action_title': 'Migrate Phenotypes'
                }
            )

@login_required
def admin_fix_breathe_dt(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_fix_breathe_dt'),
                'action_title': 'Fix Breathe Phenotypes',
                'hide_phenotype_options': True,
            }
        )

    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    with connection.cursor() as cursor:
        sql = """
        UPDATE public.clinicalcode_genericentity
        SET validation =CONCAT(validation, '21')
        WHERE name LIKE 'Acute bronchitis%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_genericentity
        SET validation =CONCAT(validation, '7')
        WHERE name LIKE 'Asthma%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_genericentity
        SET validation =CONCAT(validation, '%.')
        WHERE name LIKE 'Chronic obstructive%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_genericentity
        SET validation =CONCAT(validation, 'a.')
        WHERE name LIKE 'Empyema%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_genericentity
        SET validation =CONCAT(validation, 's.')
        WHERE name LIKE 'Influenza infection%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_genericentity
        SET validation =CONCAT(validation, 'hs')
        WHERE name LIKE 'Pertussis%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_genericentity
        SET validation ='The definition of pneumonia has not been validated'
        WHERE name LIKE 'Pneumonia%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;
        """
        cursor.execute(sql)
        print(cursor.rowcount, "record(s) affected")

    with connection.cursor() as cursor:

        historical = """
        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, '21')
        WHERE name LIKE 'Acute bronchitis%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, '7')
        WHERE name LIKE 'Asthma%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, '%.')
        WHERE name LIKE 'Chronic obstructive%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, 'a.')
        WHERE name LIKE 'Empyema%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, 's.')
        WHERE name LIKE 'Influenza infection%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, 'hs')
        WHERE name LIKE 'Pertussis%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation ='The definition of pneumonia has not been validated'
        WHERE name LIKE 'Pneumonia%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;

        UPDATE public.clinicalcode_historicalgenericentity
        SET validation =CONCAT(validation, 'hs')
        WHERE name LIKE 'Rhinitis%'
        AND template_data ->> 'phenotype_uuid' LIKE 'excel-breathe%'
        AND validation IS NOT NULL;
        """
        cursor.execute(historical)

        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html',
            {   'pk': -10,
                'action_title': 'Fix Breathe',
            }
        )

@login_required
def admin_convert_entity_groups(request):
    if settings.CLL_READ_ONLY: 
        raise PermissionDenied
    
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied
    
    # get
    if request.method == 'GET':
        return render(
            request,
            'clinicalcode/adminTemp/admin_temp_tool.html', 
            {
                'url': reverse('admin_convert_entity_groups'),
                'action_title': 'Convert groups to organisations',
                'hide_phenotype_options': True,
            }
        )
    
    # post
    if request.method != 'POST':
        raise BadRequest('Invalid')

    GROUP_LOOKUP = {
        2: 32,
        6: 60,
        7: 9,
        12: 197
    }

    entities = GenericEntity.objects \
        .filter(group_id__isnull=False)

    entity_groups = entities \
        .order_by('group_id') \
        .distinct('group_id') \
        .values_list('group_id', flat=True)

    groups = Group.objects \
        .filter(id__in=list(entity_groups))

    for entity_group in entity_groups:
        owner_id = GROUP_LOOKUP.get(entity_group)
        if not owner_id:
            continue

        current_owner = User.objects.filter(id=owner_id)
        if not current_owner.exists():
            continue
        current_owner = current_owner.first()

        current_group = Group.objects.filter(id=entity_group)
        if not current_group.exists():
            continue
        current_group = current_group.first()

        current_members = User.objects.filter(groups=current_group) \
            .exclude(id=owner_id)

        org = Organisation.objects.create(
            name=current_group.name,
            owner=current_owner
        )
        for current_member in current_members:
            member = OrganisationMembership.objects.create(
                user_id=current_member.id,
                organisation_id=org.id
            )

        current_entities = entities.filter(group_id=entity_group)
        for entity in current_entities:
            entity.organisation = org
            entity.save()

    return render(
        request,
        'clinicalcode/adminTemp/admin_temp_tool.html',
        {
            'pk': -10,
            'rowsAffected' : { '1': 'ALL'},
            'action_title': 'Convert groups to organisations',
            'hide_phenotype_options': True,
        }
    )

def get_serial_id():
    count_all = GenericEntity.objects.count()
    if count_all:
        count_all += 1
    else:
        count_all = 1
        
    return count_all

def get_agreement_date(phenotype):
    if phenotype.hdr_modified_date:
        return phenotype.hdr_modified_date
    else:
        return phenotype.hdr_created_date

def get_sex(phenotype):
    sex = str(phenotype.sex).lower().strip()
    if sex == 'male':
        return 1
    elif sex == 'female':
        return 2
    else:
        return 3

def get_type(phenotype):
    type = str(phenotype.type).lower().strip()
    if type == "biomarker":
        return 1
    elif type == "disease or syndrome":
        return 2
    elif type == "drug":
        return 3
    elif type == "lifestyle risk factor":
        return 4
    elif type == "musculoskeletal":
        return 5
    elif type == "surgical procedure":
        return 6    
    else:
        return -1

def get_custom_fields(phenotype):
    ret_data = {}
    
    ret_data['type'] = str(get_type(phenotype))
    ret_data['concept_information'] = phenotype.concept_informations
    ret_data['coding_system'] = phenotype.clinical_terminologies
    ret_data['data_sources'] = phenotype.data_sources
    ret_data['phenoflowid'] = phenotype.phenoflowid    
    ret_data['agreement_date'] = get_agreement_date(phenotype)
    ret_data['phenotype_uuid'] = phenotype.phenotype_uuid
    ret_data['event_date_range'] = phenotype.valid_event_data_range
    ret_data['sex'] = str(get_sex(phenotype))
    ret_data['source_reference'] = phenotype.source_reference
    
    return ret_data
    
def get_custom_fields_key_value(phenotype):
    """
        return one dict of col_name/col_value pairs
    """
    
    return get_custom_fields(phenotype)
