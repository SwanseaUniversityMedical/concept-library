from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db.models import F

from ...models import Tag, GenericEntity
from ...entity_utils import api_utils
from ...entity_utils import constants

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_tags(request):
    '''
        Get all tags
    '''
    tags = Tag.objects.filter(
        tag_type=constants.TAG_TYPE.TAG.value
    ) \
    .order_by('id')
    
    result = tags.annotate(
        name=F('description')
    ) \
    .values('id', 'name')

    return Response(
        data=list(result),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_tag_detail(request, tag_id):
    '''
        Get detail of specified tag by tag_id, including associated
          published entities
    '''
    tag = Tag.objects.filter(id=tag_id)
    if not tag.exists():
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
