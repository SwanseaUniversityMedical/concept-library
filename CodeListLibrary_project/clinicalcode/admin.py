from django.contrib import admin
from django.utils import timezone

import datetime

from .models import (Brand, CodingSystem, CodingSystemFilter, DataSource, Operator, Tag)
from .models.EntityClass import EntityClass
from .models.GenericEntity import GenericEntity
from .models.Template import Template
from .models.OntologyTag import OntologyTag
from .models.Organisation import Organisation
from .models.DMD_CODES import DMD_CODES

from .forms.TemplateForm import TemplateAdminForm
from .forms.EntityClassForm import EntityAdminForm
from .forms.OrganisationForms import OrganisationAdminForm, OrganisationMembershipInline, OrganisationAuthorityInline

@admin.register(OntologyTag)
class OntologyTag(admin.ModelAdmin):
    list_display = ['id', 'name', 'type_id']


@admin.register(CodingSystemFilter)
class CodingSystemFilterAdmin(admin.ModelAdmin):
    list_display = ['coding_system', 'id', 'type']


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ['description']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'description', 'display', 'tag_type', 'collection_brand']
    list_filter = ['collection_brand', 'tag_type', 'display']
    search_fields = ['description']
    exclude = ['created_by', 'updated_by']

    def save_model(self, request, obj, form, change):
        user = request.user
        instance = form.save(commit=False)

        if not change or not instance.created_by:
            instance.created_by = user

        instance.updated_by = user
        instance.modified = datetime.datetime.now()
        instance.save()
        form.save_m2m()

        return instance


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_filter = ['name', 'description', 'created', 'modified']
    list_display = ['name', 'id', 'logo_path', 'description']
    search_fields = ['name', 'id', 'description']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):    
    list_display = ['id', 'name', 'uid', 'url', 'created_by', 'updated_by', 'source']
    list_filter = ['source']
    search_fields = ['name', 'url', 'uid']
    exclude = []


@admin.register(CodingSystem)
class CodingSystemAdmin(admin.ModelAdmin):
    list_display = ['id', 'codingsystem_id', 'name', 'description'] 
    list_filter = ['name']
    search_fields = ['name', 'codingsystem_id', 'description']
    exclude = []

@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
  """
    Organisation admin representation
  """
  form = OrganisationAdminForm
  inlines = [OrganisationMembershipInline, OrganisationAuthorityInline]
  #exclude = ['created', 'owner', 'members', 'brands']

  list_filter = ['id', 'name']
  search_fields = ['id', 'name']
  list_display = ['id', 'name', 'slug']
  prepopulated_fields = {'slug': ['name']}

  def get_form(self, request, obj=None, **kwargs):
    """
      Responsible for pre-populating form data & resolving the associated model form

      Args:
        request (RequestContext): the request context of the form
        obj (dict|None): an Organisation model instance (optional; defaults to `None`)
        **kwargs (**kwargs): arbitrary form key-value pair data
      
      Returns:
        (OrganisationModelForm) - the prepared ModelForm instance
    """
    form = super(OrganisationAdmin, self).get_form(request, obj, **kwargs)
    
    if obj is None:
      form.base_fields['slug'].initial = ''
      form.base_fields['created'].initial = timezone.now()
    else:
      form.base_fields['slug'].initial = obj.slug
      form.base_fields['created'].initial = obj.created

    form.base_fields['slug'].disabled = True
    form.base_fields['slug'].help_text = 'This field is not editable'
    form.base_fields['created'].disabled = True
    form.base_fields['created'].help_text = 'This field is not editable'

    return form

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    readonly_fields = ['template_version']
    list_display = ['id', 'name', 'description', 'template_version']
    list_filter = ['name']
    search_fields = ['name']
    exclude = ['created_by', 'updated_by']
    form = TemplateAdminForm

    def save_model(self, request, obj, form, change):
        """
            - Responsible for version history
                -> template_version computed from JSONB data, never updated unless dictdiff and/or purposefully changed
            - Responsible for computing the 'layout_order' field within the template definition
                -> Iterates through the template prior to JSONB reordering and creates a 'layout_order' key [array, def. order] (Postgres stores arrays in semantic order)
                -> Adds 'order' field to the template's individual fields
        """
        if obj.definition is not None and 'fields' in obj.definition:
            order = []
            for field in obj.definition['fields']:
                obj.definition['fields'][field]['order'] = len(order)
                order.append(field)
            obj.definition['layout_order'] = order
            
            details = obj.definition.get('template_details') or { }
            version = details.get('version', None)
            if version != obj.template_version:
                obj.template_version = version
                
        if not change or not obj.created_by:
            obj.created_by = request.user

        obj.updated_by = request.user
        obj.modified = datetime.datetime.now()
        
        obj.save()



@admin.register(EntityClass)
class EntityClassAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'entity_prefix', 'entity_count', 'modified_by', 'modified']
    exclude = []
    form = EntityAdminForm

    def save_model(self, request, obj, form, change):
        if not obj.created_by or not obj.created_by.id:
            obj.created_by = request.user
        obj.modified_by = request.user
        obj.modified = timezone.now()
        obj.save()
