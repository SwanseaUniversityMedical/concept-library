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
def get_tags(request):
    """
        Get all Tags

        Available parameters:

        | Param         | Type            | Default | Desc                                                          |
        |---------------|-----------------|---------|---------------------------------------------------------------|
        | search        | `str`           | `NULL`  | Full-text search across _name_ field                   |
        | id            | `int/list[int]` | `NULL`  | Match by a single `int` _id_ field, or match by array overlap |
    """
    search = request.query_params.get('search', '')

    tags = Tag.get_brand_records_by_request(request, params={ 'tag_type': 1 })
    if tags is not None:
        if not gen_utils.is_empty_string(search) and len(search.strip()) > 1:
            tags = tags.annotate(
                    similarity=TrigramWordSimilarity(search, 'description')
                ) \
                .filter(Q(similarity__gte=0.7)) \
                .order_by('-similarity')
        else:
            tags = tags.order_by('id')

        tags = tags.annotate(
            name=F('description')
        ) \
        .values('id', 'name')


    return Response(
        data=tags.values('id', 'name'),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_tag_detail(request, tag_id):
    """
        Get detail of specified tag by tag_id, including associated
          published entities
    """
    tag = Tag.get_brand_assoc_queryset(request.BRAND_OBJECT, 'tags')
    if tag is not None:
        tag = tag.filter(id=tag_id)

    if not tag or not tag.exists():
        return Response(
            data={
                'message': 'Tag with id does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )
    tag = tag.first()

    # Get all published entities with this tag
    entities = GenericEntity.history.filter(
        publish_status=constants.APPROVAL_STATUS.APPROVED.value,
        tags__overlap=[tag_id]
    ) \
    .order_by('id', '-history_id') \
    .distinct('id')

    # Format results
    entities = api_utils.annotate_linked_entities(entities)

    result = {
        'id': tag.id,
        'name': tag.description,
        'phenotypes': list(entities)
    }

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )
