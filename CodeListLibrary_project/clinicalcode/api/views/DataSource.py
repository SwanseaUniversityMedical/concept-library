from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Subquery, OuterRef

from ...models import DataSource, Template, GenericEntity
from ...entity_utils import api_utils
from ...entity_utils import gen_utils
from ...entity_utils import constants

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_datasources(request):
    """
        Get all datasources
    """
    datasources = DataSource.objects.all().order_by('id')
    datasources = list(datasources.values('id', 'name', 'url', 'uid', 'source'))
    return Response(
        data=datasources,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_datasource_detail(request, datasource_id):
    """
        Get detail of specified datasource by datasource_id (id or HDRUK UUID for
          linkage between applications), including associated published entities
    """
    query = None
    if gen_utils.is_valid_uuid(datasource_id):
        query = { 'uid': datasource_id }
    elif gen_utils.parse_int(datasource_id, default=None) is not None:
        query = { 'id': int(datasource_id) }
    
    if not query:
        return Response(
            data={
                'message': 'Invalid id, should be datasource id or datasource UUID'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    datasource = DataSource.objects.filter(**query)
    if not datasource.exists():
        return Response(
            data={
                'message': 'Datasource with id/UUID does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )
    datasource = datasource.first()

    # Get all templates and their versions where data_sources exist
    templates = Template.history.filter(
        definition__fields__has_key='data_sources'
    ) \
    .annotate(
        was_deleted=Subquery(
            Template.history.filter(
                id=OuterRef('id'),
                history_date__gte=OuterRef('history_date'),
                history_type='-'
            )
            .order_by('id', '-history_id')
            .distinct('id')
            .values('id')
        )
    ) \
    .exclude(was_deleted__isnull=False) \
    .order_by('id', '-template_version', '-history_id') \
    .distinct('id', 'template_version')

    template_ids = list(templates.values_list('id', flat=True))
    template_versions = list(templates.values_list('template_version', flat=True))

    # Get all published entities with this datasource
    entities = GenericEntity.history.filter(
        template_id__in=template_ids,
        template_version__in=template_versions,
        publish_status=constants.APPROVAL_STATUS.APPROVED.value
    ) \
    .extra(where=[f"""
        exists(
            select 1
            from jsonb_array_elements(
                case jsonb_typeof(template_data->'data_sources') when 'array' 
                    then template_data->'data_sources' 
                    else '[]' 
                end
            ) as val
            where val in ('{datasource.id}')
        )"""
    ]) \
    .order_by('id', '-history_id') \
    .distinct('id')

    # Format results
    entities = api_utils.annotate_linked_entities(entities)

    result = {
        'id': datasource.id,
        'name': datasource.name,
        'url': datasource.url,
        'uid': datasource.uid,
        'description': datasource.description,
        'source': datasource.source,
        'phenotypes': list(entities)
    }
    
    return Response(
        data=result,
        status=status.HTTP_200_OK
    )
