from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Subquery, OuterRef
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from ..models import PublishedGenericEntity
from ..entity_utils import permission_utils
from ..entity_utils.constants import APPROVAL_STATUS

class EntityModeration(TemplateView):
  template_name = 'clinicalcode/moderation/index.html'
  template_fields = [
    'id', 'name', 'history_id', 'created', 'owner_name', 
    'group_name', 'publish_status', 'is_deleted'
  ]
  
  def __annotate_fields(self, queryset):
    annotated = queryset.annotate(
      group_name=Subquery(
        Group.objects.filter(id=OuterRef('group_id')).values('name')
      ),
      owner_name=Subquery(
        User.objects.filter(id=OuterRef('owner')).values('username')
      ),
      publish_status=Subquery(
        PublishedGenericEntity.objects.filter(
          entity_id=OuterRef('id'), entity_history_id=OuterRef('history_id')
        ).values('approval_status')
      )
    )

    return list(annotated.values(*self.template_fields))

  @method_decorator([login_required])
  def dispatch(self, request, *args, **kwargs):
    user = request.user
    if user and (user.is_superuser or permission_utils.is_member(user, "Moderators")):
      return super(EntityModeration, self).dispatch(request, *args, **kwargs)
    
    raise PermissionDenied
    
  def get_context_data(self, *args, **kwargs):
    context = super(EntityModeration, self).get_context_data(*args, **kwargs)
    request = self.request

    requested_content = self.__annotate_fields(
      permission_utils.get_accessible_entities(
        request, consider_user_perms=False, status=[APPROVAL_STATUS.REQUESTED]
      )
    )

    pending_content = self.__annotate_fields(
      permission_utils.get_accessible_entities(
        request, consider_user_perms=False, status=[APPROVAL_STATUS.PENDING]
      )
    )

    return context | {
      'requested_content': requested_content,
      'pending_content': pending_content
    }

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)
