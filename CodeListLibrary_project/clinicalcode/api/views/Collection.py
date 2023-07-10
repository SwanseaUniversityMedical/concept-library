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
def get_collections(request):
    '''
        Get all collections
    '''
    collections = Tag.objects.filter(
        tag_type=constants.TAG_TYPE.COLLECTION.value
    ) \
    .order_by('id')
    
    result = collections.annotate(
        name=F('description')
    ) \
    .values('id', 'name')

    return Response(
        data=list(result),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_collection_detail(request, collection_id):
    '''
        Get detail of specified collection by collection_id, including associated
          published entities
    '''
    collection = Tag.objects.filter(id=collection_id)
    if not collection.exists():
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
