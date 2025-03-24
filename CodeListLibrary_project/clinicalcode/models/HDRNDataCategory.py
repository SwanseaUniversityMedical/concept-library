from django.db import models
from django.db.models import Q
from django.core.paginator import EmptyPage, Paginator
from django.contrib.postgres.indexes import GinIndex

from clinicalcode.entity_utils import gen_utils, model_utils, constants
from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNDataCategory(TimeStampedModel):
	"""
	HDRN Data Categories (e.g. Phenotype Type)
	"""
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=False, null=False, blank=False)
	description = models.TextField(null=True, blank=True)
	metadata = models.JSONField(blank=True, null=True)

	@staticmethod
	def get_brand_records_by_request(request, params=None, default=None):
		user = request.user if request.user is not None and request.user.is_authenticated else None
		brand = model_utils.try_get_brand(request)
		if (brand is not None and brand.name == 'HDRN') or (brand is None and user and user.is_superuser):
			records = HDRNDataCategory.objects.all()

		if records is None:
			return default

		if not isinstance(params, dict):
			params = { }

		search = params.pop('search', None)

		query = gen_utils.parse_model_field_query(HDRNDataCategory, params, ignored_fields=['description'])
		if query is not None:
			records = records.filter(**query)

		if not gen_utils.is_empty_string(search) and len(search) >= 3:
			records = records.filter(Q(name__icontains=search) | Q(description__icontains=search))

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
		indexes = [
			GinIndex(name='hdrn_dcnm_trgm_idx', fields=['name'], opclasses=['gin_trgm_ops']),
		]

	def __str__(self):
		return self.name
