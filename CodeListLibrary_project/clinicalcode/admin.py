from django.contrib import admin
from django.contrib.auth.models import Group, User

from .models import (Brand, CodingSystem, CodingSystemFilter, DataSource, Operator, Tag)

from .models.EntityClass import EntityClass
from .models.GenericEntity import GenericEntity
from .models.Template import Template
from .models.BaseTemplate import BaseTemplate
from .forms.TemplateForm import TemplateAdminForm, BaseTemplateAdminForm

# from forms import GroupAdminForm
# from django import forms
# from django.forms.models import inlineformset_factory, ModelChoiceField

# Register your models here.

@admin.register(CodingSystemFilter)
class CodingSystemFilterAdmin(admin.ModelAdmin):
    list_display = ['coding_system', 'id', 'type']


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ['description']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'description', 'display', 'tag_type', 'collection_brand']  #'updated_by' 'created_by' , 'created', 'modified'
    list_filter = ['collection_brand', 'tag_type', 'display']
    search_fields = ['description']
    exclude = ['created_by', 'updated_by']

    def save_model(self, request, obj, form, change):
        user = request.user
        instance = form.save(commit=False)

        if not change or not instance.created_by:
            instance.created_by = user

        instance.updated_by = user
        instance.save()
        form.save_m2m()

        return instance


#admin.site.register(Brand)
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'id', 'logo_path', 'owner', 'description']
    list_filter = ['name', 'description', 'created', 'modified', 'owner']
    search_fields = ['name', 'id', 'description']
    exclude = ['created_by', 'updated_by']


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

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    readonly_fields = ['template_version']
    list_display = ['id', 'name', 'description', 'template_version']
    list_filter = ['name']
    search_fields = ['name']
    exclude = ['created_by', 'updated_by']
    form = TemplateAdminForm

    def save_model(self, request, obj, form, change):
        '''
            - Responsible for version history
                -> template_version computed from JSONB data, never updated unless dictdiff and/or purposefully changed
            - Responsible for computing the 'layout_order' field within the template definition
                -> Iterates through the template prior to JSONB reordering and creates a 'layout_order' key [array, def. order] (Postgres stores arrays in semantic order)
                -> Adds 'order' field to the template's individual fields
        '''
        if obj.definition is not None and 'fields' in obj.definition:
            order = []
            for field in obj.definition['fields']:
                obj.definition['fields'][field]['order'] = len(order)
                order.append(field)
            obj.definition['layout_order'] = order
            
            version = obj.definition.get('version', None)
            if version != obj.template_version:
                obj.template_version = version
        
        obj.save()
    
@admin.register(GenericEntity)
class GenericEntityAdmin(admin.ModelAdmin):
    readonly_fields = ['template_version']
    list_display = ['id', 'name', 'template', 'template_version']
    exclude = []

@admin.register(EntityClass)
class EntityClassAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'entity_prefix', 'entity_count']
    exclude = []

@admin.register(BaseTemplate)
class BaseTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    exclude = []
    form = BaseTemplateAdminForm

    def save_model(self, request, obj, form, change):
        '''
            - Responsible for computing the 'layout_order' field within the template definition
                -> Iterates through the template prior to JSONB reordering and creates a 'layout_order' key [array, def. order] (Postgres stores arrays in semantic order)
                -> Adds 'order' field to the template's individual fields
        '''
        if obj.definition is not None:
            order = []
            for field in obj.definition:
                obj.definition[field]['order'] = len(order)
                order.append(field)
            obj.definition['layout_order'] = order
        
        obj.save()

#admin.site.register(CodingSystem)

# ############################################
# # Unregister the original Group admin.
# admin.site.unregister(Group)
#
# # Create a new Group admin.
# class GroupAdmin(admin.ModelAdmin):
#     # Use our custom form.
#     form = GroupAdminForm
#     #form_class = GroupAdminForm
#     # Filter permissions horizontal as well.
#     filter_horizontal = ['permissions']
#
# # Register the new Group ModelAdmin.
# admin.site.register(Group, GroupAdmin)
