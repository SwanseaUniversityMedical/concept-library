from django.db import connection
from django.db.models import Q
from functools import cmp_to_key

import datetime
import json

from ..models import GenericEntity, Template, Statistics, Brand, CodingSystem, DataSource, PublishedGenericEntity, Tag
from . import template_utils, constants, model_utils, entity_db_utils, concept_utils

def sort_by_count(a, b):
    """
        Used to sort filter statistics in descending order
    """
    count0 = a['count']
    count1 = b['count']
    if count0 < count1:
        return 1
    elif count0 > count1:
        return -1
    return 0

def get_field_values(field, validation, struct):
    value = None
    if 'options' in validation:
        value = template_utils.get_options_value(field, struct)
    elif 'source' in validation:
        value = template_utils.get_sourced_value(field, struct)
    return value

def transform_counted_field(data):
    sort_fn = cmp_to_key(sort_by_count)
    array = [
        {
            'pk': pk,
            'value': packet['value'],
            'count': packet['count']
        } for pk, packet in data.items()
    ]
    array.sort(key=sort_fn)
    return array

def try_get_cached_data(cache, entity, template, field, field_value, validation, struct, brand=None):
    if template is None or not isinstance(cache, dict):
        return get_field_values(field_value, validation, struct)
    
    if brand is not None:
        cache_key = f'{brand.name}__{field}__{field_value}__{template.id}__{template.template_version}'
    else:
        cache_key = f'{field}__{field_value}__{template.id}__{template.template_version}'
    
    if cache_key not in cache:
        value = get_field_values(field_value, validation, struct)
        if value is None:
            return None
        
        cache[cache_key] = value
        return value
    
    return cache[cache_key]

def build_statistics(statistics, entity, field, struct, data_cache=None, template_entity=None, brand=None):
    if struct is None:
        return
    
    if 'search' not in struct:
        return

    if 'filterable' not in struct.get('search'):
        return
    
    validation = template_utils.try_get_content(struct, 'validation')
    if validation is None:
        return
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return
    
    entity_field = template_utils.get_entity_field(entity, field)
    if entity_field is None:
        return

    stats = statistics[field] if field in statistics else { }
    if field_type == 'enum':
        value = try_get_cached_data(data_cache, entity, template_entity, field, entity_field, validation, struct, brand=brand)
        
        if value is not None:
            if entity_field not in stats:
                stats[entity_field] = {
                    'value': value,
                    'count': 0
                }
            
            stats[entity_field]['count'] += 1
    elif field_type == 'int_array':
        if 'source' in validation:
            for item in entity_field:
                value = try_get_cached_data(data_cache, entity, template_entity, field, item, validation, struct, brand=brand)
                if value is None:
                    continue
                if item not in stats:
                    stats[item] = {
                        'value': value,
                        'count': 0
                    }
                
                stats[item]['count'] += 1
    else:
        return
    
    statistics[field] = stats

def compute_statistics(statistics, entity, data_cache=None, template_cache=None, brand=None):
    if not template_utils.is_data_safe(entity):
        return
    
    template_id = entity.template.id if entity.template is not None else None
    template_version = entity.template_version
    if template_id is None or template_version is None:
        return

    template = None
    layout = None
    if isinstance(template_cache, dict):
        cached = template_cache.get(f'{template_id}/{template_version}')
        if cached is not None:
            template = cached.get('template')
            layout = cached.get('layout')
    
    if template is None or layout is None:
        template = Template.history.filter(
            id=entity.template.id,
            template_version=entity.template_version
        ) \
        .latest_of_each() \
        .distinct()

        if not template.exists():
            return
        
        template = template.first()
        layout = template_utils.get_merged_definition(template)
        if not layout:
            return
        
        if isinstance(template_cache, dict):
            template_cache[f'{template_id}/{template_version}'] = { 'template': template, 'layout': layout }

    for field, struct in layout.get('fields').items():
        if not isinstance(struct, dict):
            continue


        build_statistics(statistics['all'], entity, field, struct, data_cache=data_cache, template_entity=template, brand=brand)

        if entity.publish_status == constants.APPROVAL_STATUS.APPROVED:
            build_statistics(statistics['published'], entity, field, struct, data_cache=data_cache, template_entity=template, brand=brand)

def collate_statistics(entities, data_cache=None, template_cache=None, brand=None):
    statistics = {
        'published': { },
        'all': { },
    }

    if brand is not None:
        collection_ids = model_utils.get_brand_collection_ids(brand.name)
        entities = entities.filter(Q(brands__overlap=[brand.id]) | Q(collections__overlap=collection_ids))

    for entity in entities:
        compute_statistics(statistics, entity, data_cache, template_cache, brand)

    for field, all_data in statistics['all'].items():
        statistics['all'][field] = transform_counted_field(all_data)

        published_data = statistics['published'].get(field)
        if published_data is not None:
            statistics['published'][field] = transform_counted_field(published_data)

    return statistics

def collect_statistics(request):
    """
        Need to change this for several reasons:
            1. We can utilise receivers and signals so we don't do this as a cronjob
            2. Big O notation for this implementation is not great
    """
    user = request.user if request else None
    cache = { }
    template_cache = { }

    all_entities = GenericEntity.objects.all()

    to_update = [ ]
    to_create = [ ]
    for brand in Brand.objects.all():
        stats = collate_statistics(
            all_entities,
            data_cache=cache,
            template_cache=template_cache,
            brand=brand
        )

        obj = Statistics.objects.filter(
            org=brand.name,
            type='GenericEntity',
        )

        if obj.exists():
            obj = obj.first()
            obj.stat = stats
            obj.updated_by = user
            to_update.append(obj)
            continue

        obj = Statistics(
            org=brand.name,
            type='GenericEntity',
            stat=stats,
            created_by=user
        )
        to_create.append(obj)
    
    stats = collate_statistics(
        all_entities,
        data_cache=cache,
        template_cache=template_cache
    )

    obj = Statistics.objects.filter(
        org='ALL',
        type='GenericEntity',
    )

    if obj.exists():
        obj = obj.first()
        obj.stat = stats
        obj.updated_by = user
        to_update.append(obj)
    else:
        obj = Statistics(
            org='ALL',
            type='GenericEntity',
            stat=stats,
            created_by=user
        )
        to_create.append(obj)
    
    # Create / Update stat objs
    Statistics.objects.bulk_create(to_create)
    Statistics.objects.bulk_update(to_update, ['stat', 'updated_by'])

    clear_statistics_history()


def clear_statistics_history():
    """
        leave only the last record per day for each statistics category
    """
    with connection.cursor() as cursor:
        sql = """ 
                WITH tbl AS (
                            SELECT *
                            FROM
                            (
                                SELECT 
                                    ROW_NUMBER () OVER (PARTITION BY org, type, date(history_date) ORDER BY history_date DESC) rn
                                    , *
                                FROM clinicalcode_historicalstatistics 
                            )t
                )
                DELETE FROM clinicalcode_historicalstatistics WHERE history_id NOT IN(SELECT history_id FROM tbl WHERE rn = 1) ;
             """
        cursor.execute(sql)


def compute_homepage_stats(request, brand):
    stat = get_homepage_stats(request, brand)

    if Statistics.objects.all().filter(org__iexact=brand, type__iexact='landing-page').exists():
        stats = Statistics.objects.get(org__iexact=brand, type__iexact='landing-page')
        stats.stat = stat
        stats.updated_by = [None, request.user][request.user.is_authenticated]
        stats.modified = datetime.datetime.now()
        stats.save()

        clear_statistics_history()
        return [stat, stats.id]

    obj, created = Statistics.objects.get_or_create(
        org=brand,
        type='landing-page',
        stat=stat,
        created_by=[None, request.user][request.user.is_authenticated]
    )

    clear_statistics_history()
    return [stat, obj.id]


def save_homepage_stats(request, brand=None):
    if brand is not None:
        return compute_homepage_stats(request, brand)
    
    brands = Brand.objects.all()
    result = [ ]
    for brand in brands:
        result.append(compute_homepage_stats(request, brand.name))
    result.append(compute_homepage_stats(request, 'ALL'))
    return result


def get_homepage_stats(request, brand=None):
    '''
        get homepage statistics for display.
    '''

    if brand is None:
        brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'
    
    collection_ids = [ ]
    if brand == 'ALL':
        collection_ids = model_utils.get_brand_collection_ids('HDRUK')
        collection_ids = [str(i) for i in collection_ids]
    else:
        collection_ids = Tag.objects.filter(tag_type=2)
        collection_ids = [str(i) for i in collection_ids]
    
    published_phenotypes = entity_db_utils.get_visible_live_or_published_generic_entity_versions(
        request,
        get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published
        exclude_deleted=True,
        show_top_version_only=False,
        force_brand=('' if brand == 'ALL' else brand),
        force_get_live_and_or_published_ver=2  # get published data
    )

    published_phenotypes_id_version = entity_db_utils.get_list_of_visible_entity_ids(published_phenotypes, return_id_or_history_id="both")
    published_phenotypes_ids = list(set([p[0] for p in published_phenotypes_id_version]))

    published_concepts_id_version = entity_db_utils.get_concept_ids_from_phenotypes(published_phenotypes, return_id_or_history_id="both")
    published_concepts_ids = list(set([c[0] for c in published_concepts_id_version]))

    return get_phenotype_data(published_phenotypes) | {
        'published_concept_count': len(published_concepts_ids),
        'published_phenotype_count': len(published_phenotypes_ids),
    }


def get_phenotype_data(published_phenotypes):
    coding_systems_ids = []
    ds_ids = [] 
    count = 0
    for p in published_phenotypes:
        if p['template_id'] == 1:
            template_data = None
            try:
                template_data = p.get('template_data') if isinstance(p, dict) else getattr(p, 'template_data')
                template_data = json.loads(template_data) if template_data is not None else None
            except:
                continue

            if not isinstance(template_data, dict):
                continue
            
            concepts = template_data.get('concept_information')
            data_sources = template_data.get('data_sources')
            coding_system = template_data.get('coding_system')

            if coding_system is not None:
                coding_systems_ids = list(set(coding_systems_ids + coding_system))

            if data_sources is not None:
                ds_ids = list(set(ds_ids + data_sources))

            if concepts:
                pid, phd = p.get('id'), p.get('history_id')
                if pid is not None and phd is not None:
                    codecount = get_published_phenotype_code_count(
                        phenotype_id=pid, 
                        phenotype_history_id=phd, 
                        concept_information=concepts
                    )
                    count = count + codecount

    # make sure coding system exists
    unique_coding_systems_ids = list(set(coding_systems_ids))
    unique_coding_systems_ids_list = list(CodingSystem.objects.filter(id__in=unique_coding_systems_ids).values_list('id', flat=True))

    # make sure data-source exists
    unique_ds_ids = list(set(ds_ids))
    unique_ds_ids_list = list(DataSource.objects.filter(id__in=unique_ds_ids).values_list('id', flat=True))

    return {
        'clinical_terminologies': len(unique_coding_systems_ids_list),
        'published_clinical_codes': count,
        'datasources_component_count': len(unique_ds_ids_list),  
    }


def get_published_phenotype_code_count(phenotype_id, phenotype_history_id, concept_information):
    """
        return the code count of a published phenotype version.
        will save this count in Publishedphenotype table if not already so.
    """

    codecount = 0
    if concept_information:
        published_phenotype = PublishedGenericEntity.objects.filter(entity_id=phenotype_id, entity_history_id=phenotype_history_id)
        if not published_phenotype.exists():
            return codecount

        published_phenotype = published_phenotype.first()
        saved_codecount = published_phenotype.code_count

        # calc the code count (sum all concepts in this phenotype)
        if saved_codecount is None or saved_codecount == '' or saved_codecount == 0:
            for c in concept_information:
                codelist = concept_utils.get_concept_codelist(
                    c['concept_id'],
                    c['concept_version_id'],
                    incl_attributes=False
                )
                    
                codecount += len(codelist)

            published_phenotype.code_count = codecount
            published_phenotype.save()
            return codecount

        return saved_codecount

    return codecount
