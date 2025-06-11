from django.db import models
from django.http import HttpRequest
from django.db.models import Q
from simple_history.models import HistoricalRecords
from django.core.paginator import EmptyPage, Paginator, Page
from rest_framework.request import Request
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model

from .Brand import Brand
from .EntityClass import EntityClass
from .TimeStampedModel import TimeStampedModel
from clinicalcode.entity_utils import constants, gen_utils, model_utils

User = get_user_model()

class Template(TimeStampedModel):
    """
        Template
            @desc describes the structure of the data for that type of generic entity
                and holds statistics information e.g.
                    - count of each entity within this template
                    - count of tag/collection/datasource/coding system/

                also holds information relating to represents the filterable fields as a hasmap to improve performance
                as well as ensuring order is kept through creating a 'layout_order' field and an 'order' field within
                the template definition
    """

    ''' Metadata '''
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    definition = models.JSONField(blank=True, null=True, default=dict)
    entity_class = models.ForeignKey(EntityClass, on_delete=models.SET_NULL, null=True, related_name='entity_class_type')
    template_version = models.IntegerField(null=True, editable=False)
    hide_on_create = models.BooleanField(null=False, default=False)

    ''' Brand behaviour '''
    brands = ArrayField(models.IntegerField(), blank=True, null=True)

    ''' Instance data '''
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='template_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='template_updated')
    history = HistoricalRecords()

    ''' Static methods '''
    @staticmethod
    def get_verbose_names(*args, **kwargs):
        return { 'verbose_name': Template._meta.verbose_name, 'verbose_name_plural': Template._meta.verbose_name_plural }

    @staticmethod
    def get_brand_records_by_request(request, params=None):
        brand = model_utils.try_get_brand(request)

        records = None
        if brand is None:
            records = Template.objects.all()
        elif isinstance(brand, Brand):
            vis_rules = brand.get_vis_rules()
            if isinstance(vis_rules, dict):
                allow_null = vis_rules.get('allow_null')
                allowed_brands = vis_rules.get('ids')
                if isinstance(allowed_brands, list) and isinstance(allow_null, bool):
                    records = Template.objects.filter(Q(brands__overlap=allowed_brands) | Q(brands__isnull=allow_null))
                elif isinstance(allowed_brands, list):
                    records = Template.objects.filter(brands__overlap=allowed_brands)
                elif isinstance(allow_null, bool) and allow_null:
                    records = Template.objects.filter(brands__isnull=True)

            if records is None:
                records = Template.objects.filter(brands__overlap=[brand.id])

        if records is None:
            return Template.objects.none()

        if not isinstance(params, dict):
            params = { }

        if isinstance(request, Request) and hasattr(request, 'query_params'):
            params = { key: value for key, value in request.query_params.items() } | params
        elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
            params = { key: value for key, value in request.GET.dict().items() } | params

        search = params.get('search', None)
        query = gen_utils.parse_model_field_query(Template, params, ignored_fields=['description'])
        if query is not None:
            records = records.filter(**query)

        if not gen_utils.is_empty_string(search) and len(search) >= 3:
            records = records.filter(Q(name__icontains=search) | Q(description__icontains=search))

        records = records.order_by('id')
        return records

    @staticmethod
    def get_brand_paginated_records_by_request(request, params=None):
        if not isinstance(params, dict):
            params = { }

        if isinstance(request, Request) and hasattr(request, 'query_params'):
            params = { key: value for key, value in request.query_params.items() } | params
        elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
            params = { key: value for key, value in request.GET.dict().items() } | params

        records = Template.get_brand_records_by_request(request, params)

        page = gen_utils.try_value_as_type(params.get('page'), 'int', default=1)
        page = max(page, 1)

        page_size = params.get('page_size', '1')
        if page_size not in constants.PAGE_RESULTS_SIZE:
            page_size = constants.PAGE_RESULTS_SIZE.get('1')
        else:
            page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

        if records is None:
            return Page(Template.objects.none(), 0, Paginator([], page_size, allow_empty_first_page=True))

        pagination = Paginator(records, page_size, allow_empty_first_page=True)
        try:
            page_obj = pagination.page(page)
        except EmptyPage:
            page_obj = pagination.page(pagination.num_pages)
        return page_obj


    ''' Public methods '''
    def save(self,  *args, **kwargs):
        """
            [!] Note:
                1. The 'template_version' field is computed from JSONB data - it's non-editable.
                   When trying to query templates using historical records, the 'template_version' field can be used safely
                
                2. 'layout_order' fields are added to the template.definition when saving and can be queried using get_ordered_definition within template_utils

                3. Entity type/prefix can be queried through template.entity_class
        """
                  
        super(Template, self).save(*args, **kwargs)

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret


    ''' Meta '''
    class Meta:
        ordering = ('name', )
        verbose_name = _('Template')
        verbose_name_plural = _('Templates')


    ''' Dunder methods '''
    def __str__(self):
        return self.name
