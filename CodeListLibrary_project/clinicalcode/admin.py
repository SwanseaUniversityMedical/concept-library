from django.contrib import admin
from .models import CodingSystem, CodingSystemFilter, Tag, Operator, Brand, DataSource
from django.contrib.auth.models import User, Group

# from forms import GroupAdminForm
# from django import forms
# from django.forms.models import inlineformset_factory, ModelChoiceField


# Register your models here.
admin.site.register(CodingSystem)


@admin.register(CodingSystemFilter)
class CodingSystemFilterAdmin(admin.ModelAdmin):
    list_display = ['coding_system', 'id', 'type']


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ['description']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'description', 'get_display_display', 'created_by', 'created', 'updated_by', 'modified']
    list_filter = ['description', 'created', 'modified']
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
    list_display = ['name', 'uid', 'url',  'description']
    list_filter = ['name', 'uid', 'description', 'created', 'modified']
    search_fields = ['name', 'uid', 'description']
    exclude = ['created_by', 'updated_by']
    
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





