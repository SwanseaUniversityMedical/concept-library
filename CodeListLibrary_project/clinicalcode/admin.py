from django.contrib import admin
from django.contrib.auth.models import Group, User

from .models import (Brand, CodingSystem, CodingSystemFilter, DataSource, Operator, Tag, Template, GenericEntity)
from .forms.TemplateForm import TemplateAdminForm

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
class Template(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'entity_count']
    list_filter = ['name']
    search_fields = ['name']
    exclude = ['created_by', 'updated_by']
    form = TemplateAdminForm

    def save_model(self, request, obj, form, change):
        '''
            - Responsible for building and modifying the 'entity_order' field
                -> Iterates through the template prior to JSONB reordering and stores as array (Postgres stores arrays in semantic order)
        '''
        if form.cleaned_data['update_order'] or not change:
            if obj.definition is not None and 'fields' in obj.definition:
                order = []
                for field in obj.definition['fields']:
                    order.append(field)
                obj.entity_order = order

        super().save_model(request, obj, form, change)

    
@admin.register(GenericEntity)
class GenericEntityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'template', 'entity_prefix', 'entity_id']
    exclude = []

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
