from django.db import models
from django.http import HttpRequest
from simple_history.models import HistoricalRecords
from django.core.paginator import EmptyPage, Paginator, Page
from rest_framework.request import Request
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from clinicalcode.models.Brand import Brand
from clinicalcode.entity_utils import constants, gen_utils, filter_utils, model_utils
from clinicalcode.models.TimeStampedModel import TimeStampedModel

User = get_user_model()

class Tag(TimeStampedModel):
    default = 1
    primary = 2
    success = 3
    info = 4
    warning = 5
    danger = 6

    DISPLAY_CHOICES = ((default, 'default'), (primary, 'primary'),
                       (success, 'success'), (info, 'info'),
                       (warning, 'warning'), (danger, 'danger'))

    tag = 1
    collection = 2

    TAG_TYPES = ((tag, 'tag'), (collection, 'collection'))
    description = models.CharField(max_length=50)
    display = models.IntegerField(choices=DISPLAY_CHOICES, default=1)
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="tags_created")
    updated_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="tags_updated")

    tag_type = models.IntegerField(choices=TAG_TYPES, default=1)
    collection_brand = models.ForeignKey(Brand,
                                         blank=True,
                                         on_delete=models.SET_NULL,
                                         null=True,
                                         related_name="tags_collection_brand")

    history = HistoricalRecords()

    @staticmethod
    def get_verbose_names(subtype=None, *args, **kwargs):
        is_str = isinstance(subtype, str)
        type_id = gen_utils.parse_int(subtype) if is_str else subtype

        is_valid = isinstance(type_id, int)
        if not is_valid and is_str:
            subtype = subtype.lower()
            if subtype.startswith('tag'):
                type_id = 1
            elif subtype.startswith('collection'):
                type_id = 2
            else:
                type_id = 1
        elif not is_valid:
            type_id = 1

        if type_id == 1 or not (1 <= type_id <= 2):
            verbose_name = _('Tag')
            verbose_name_plural = _('Tags')
        elif type_id == 2:
            verbose_name = _('Collection')
            verbose_name_plural = _('Collections')
        return { 'verbose_name': verbose_name, 'verbose_name_plural': verbose_name_plural }

    @staticmethod
    def get_brand_records_by_request(request, params=None):
        brand = model_utils.try_get_brand(request)

        if not isinstance(params, dict):
            params = { }

        if isinstance(request, Request) and hasattr(request, 'query_params'):
            params = { key: value for key, value in request.query_params.items() } | params
        elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
            params = { key: value for key, value in request.GET.dict().items() } | params

        tag_type = params.pop('tag_type', 1)
        tag_name = 'tags'
        if tag_type == 2:
            tag_name = 'collections'

        records = None
        if brand:
            source = constants.metadata.get(tag_name, {}) \
                .get('validation', {}) \
                .get('source', {}) \
                .get('filter', {}) \
                .get('source_by_brand', None)

            if source is not None:
                result = filter_utils.DataTypeFilters.try_generate_filter(
                    desired_filter='brand_filter',
                    expected_params=None,
                    source_value=source,
                    column_name='collection_brand',
                    brand_target=brand
                )

                if isinstance(result, list) and len(result) > 0:
                    records = Tag.objects.filter(*result)

            if records is None:
                records = Tag.objects.filter(collection_brand=brand.id, tag_type=tag_type)
        else:
            records = Tag.objects.filter(tag_type=tag_type)

        if records is None:
            return QuerySet()

        search = params.pop('search', None)
        query = gen_utils.parse_model_field_query(Tag, params, ignored_fields=['description'])
        if query is not None:
            records = records.filter(**query)

        if not gen_utils.is_empty_string(search) and len(search) >= 3:
            records = records.filter(description__icontains=search)

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

        records = Tag.get_brand_records_by_request(request, params)
        if records is None:
            return Page(QuerySet(), 0, Paginator([], page_size, allow_empty_first_page=True))

        page = params.get('page', 1)
        page = max(page, 1)

        page_size = params.get('page_size', '1')
        if page_size not in constants.PAGE_RESULTS_SIZE:
            page_size = constants.PAGE_RESULTS_SIZE.get('1')
        else:
            page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

        pagination = Paginator(records, page_size, allow_empty_first_page=True)
        try:
            page_obj = pagination.page(page)
        except EmptyPage:
            page_obj = pagination.page(pagination.num_pages)
        return page_obj

    class Meta:
        ordering = ('description', )
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')

    def __str__(self):
        return self.description
