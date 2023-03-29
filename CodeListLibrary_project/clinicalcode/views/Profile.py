from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Subquery, OuterRef
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from ..models import PublishedGenericEntity
from ..entity_utils import permission_utils
from ..entity_utils.constants import APPROVAL_STATUS

class MyProfile(TemplateView):
  template_name = 'clinicalcode/profile/my_profile.html'

  @method_decorator([login_required])
  def dispatch(self, request, *args, **kwargs):
    return super(MyProfile, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(MyProfile, self).get_context_data(*args, **kwargs)
    request = self.request

    return context | {}

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)

class MyCollection(TemplateView):
  template_name = 'clinicalcode/profile/my_collection.html'
  template_fields = [
    'id', 'name', 'history_id', 'updated', 'owner_name', 
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
    return super(MyCollection, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(MyCollection, self).get_context_data(*args, **kwargs)
    request = self.request

    published_content = self.__annotate_fields(
      permission_utils.get_accessible_entities(
        request, consider_user_perms=False, status=[APPROVAL_STATUS.APPROVED]
      )
    )

    progress_content = self.__annotate_fields(
      permission_utils.get_accessible_entities(
        request, consider_user_perms=False, status=[
          APPROVAL_STATUS.REQUESTED, 
          APPROVAL_STATUS.PENDING,
          APPROVAL_STATUS.REJECTED
        ]
      )
    )

    draft_content = self.__annotate_fields(
      permission_utils.get_accessible_entities(
        request, consider_user_perms=False, status=None
      )
    )
    
    archived_content = self.__annotate_fields(
      permission_utils.get_accessible_entities(
        request, consider_user_perms=False, status=[APPROVAL_STATUS.ANY], only_deleted=True
      )
    )

    return context | {
      'published_content': published_content,
      'progress_content': progress_content,
      'draft_content': draft_content,
      'archived_content': archived_content
    }

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)
