from rest_framework import status
from django.db.models import F, Q
from rest_framework.response import Response
from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.postgres.search import TrigramWordSimilarity

from ...models import Tag, GenericEntity
from ...entity_utils import constants, gen_utils, api_utils

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_collections(request):
    """
        Get all Collections

        Available parameters:

        | Param         | Type            | Default | Desc                                                          |
        |---------------|-----------------|---------|---------------------------------------------------------------|
        | search        | `str`           | `NULL`  | Full-text search across _name_ field                   |
        | id            | `int/list[int]` | `NULL`  | Match by a single `int` _id_ field, or match by array overlap |
    """
    search = request.query_params.get('search', '')

    collections = Tag.get_brand_records_by_request(request, params={ 'tag_type': 2 })
    if collections is not None:
        if not gen_utils.is_empty_string(search) and len(search.strip()) > 1:
            collections = collections.annotate(
                    similarity=TrigramWordSimilarity(search, 'description')
                ) \
                .filter(Q(similarity__gte=0.7)) \
                .order_by('-similarity')
        else:
            collections = collections.order_by('id')

        collections = collections.annotate(
            name=F('description')
        ) \
        .values('id', 'name')

    return Response(
        data=collections.values('id', 'name'),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_collection_detail(request, collection_id):
    """
        Get detail of specified collection by collection_id, including associated
          published entities
    """
    collection = Tag.get_brand_assoc_queryset(request.BRAND_OBJECT, 'collections')
    if collection is not None:
        collection = collection.filter(id=collection_id)

    if not collection or not collection.exists():
        return Response(
            data={
                'message': 'Collection with id does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )
    collection = collection.first()

    # Get all published entities with this collection
    entities = GenericEntity.history.filter(
        publish_status=constants.APPROVAL_STATUS.APPROVED.value,
        collections__overlap=[collection_id]
    ) \
    .order_by('id', '-history_id') \
    .distinct('id')
    
    # Format results
    entities = api_utils.annotate_linked_entities(entities)

    result = {
        'id': collection.id,
        'name': collection.description,
        'phenotypes': list(entities)
    }

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )
