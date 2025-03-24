from django.db import models
from django.db.models import Model
from simple_history.models import HistoricalRecords
from django.core.paginator import EmptyPage, Paginator
from django.contrib.auth.models import User

import inspect

from clinicalcode.models.Brand import Brand
from clinicalcode.entity_utils import constants, gen_utils, filter_utils
from clinicalcode.models.TimeStampedModel import TimeStampedModel

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
    def get_brand_records_by_request(request, params=None, default=None):
        brand = request.BRAND_OBJECT
        if not inspect.isclass(brand) or not issubclass(brand, Model):
            brand = request.CURRENT_BRAND
            if not gen_utils.is_empty_string(brand) and brand.lower() != 'ALL':
                brand = Brand.objects.filter(name__iexact=brand)
                if brand.exists():
                    brand = brand.first()

        if not isinstance(params, dict):
            params = { }

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

        search = params.pop('search', None)
        query = gen_utils.parse_model_field_query(Tag, params, ignored_fields=['description'])
        if query is not None:
            records = records.filter(**query)

        if not gen_utils.is_empty_string(search) and len(search) >= 3:
            records = records.filter(description__icontains=search)

        records = records.order_by('id')

        page = gen_utils.try_get_param(request, 'page', params.get('page', 1))
        page = max(page, 1)

        page_size = gen_utils.try_get_param(request, 'page_size', params.get('page_size', '1'))
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

    def __str__(self):
        return self.description
