from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Subquery, OuterRef
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from ..models.Organisation import Organisation
from ..entity_utils import permission_utils, constants

class EntityModeration(TemplateView):
  template_name = 'clinicalcode/moderation/index.html'
  template_fields = [
    'id', 'name', 'history_id', 'created', 'owner_name', 
    'group_name', 'publish_status', 'is_deleted'
  ]
  
  def __annotate_fields(self, queryset):
    if not queryset:
      return list()
    
    annotated = queryset.annotate(
      group_name=Subquery(
        Organisation.objects.filter(id=OuterRef('organisation_id')).values('name')
      ),
      owner_name=Subquery(
        User.objects.filter(id=OuterRef('owner')).values('username')
      )
    )

    return list(annotated.values(*self.template_fields))

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    user = request.user
    if user and (user.is_superuser or permission_utils.is_member(user, "Moderators")):
      return super(EntityModeration, self).dispatch(request, *args, **kwargs)
    
    raise PermissionDenied
    
  def get_context_data(self, *args, **kwargs):
    context = super(EntityModeration, self).get_context_data(*args, **kwargs)
    request = self.request

    requested_content = self.__annotate_fields(
      permission_utils.get_moderation_entities(
        request, 
        status=[constants.APPROVAL_STATUS.REQUESTED]
      )
    )

    pending_content = self.__annotate_fields(
      permission_utils.get_moderation_entities(
        request, 
        status=[constants.APPROVAL_STATUS.PENDING]
      )
    )

    return context | {
      'requested_content': requested_content,
      'pending_content': pending_content
    }

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)
