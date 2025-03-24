from django.db import models
from django.db.models import Q
from django.core.paginator import EmptyPage, Paginator
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex

from clinicalcode.entity_utils import gen_utils, model_utils, constants
from clinicalcode.models.HDRNSite import HDRNSite
from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNDataAsset(TimeStampedModel):
	"""
	HDRN Inventory Data Assets
	"""
	# Top-level
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=False, null=False, blank=False)
	description = models.TextField(null=True, blank=True)

	# Reference
	hdrn_id = models.IntegerField(null=True, blank=True)
	hdrn_uuid = models.UUIDField(primary_key=False, null=True, blank=True)

	# Metadata
	link = models.URLField(max_length=500, blank=True, null=True)
	site = models.ForeignKey(HDRNSite, on_delete=models.SET_NULL, null=True, related_name='data_assets')
	years = models.CharField(max_length=256, unique=False, null=True, blank=True)
	scope = models.TextField(null=True, blank=True)
	region = models.CharField(max_length=2048, unique=False, null=True, blank=True)
	purpose = models.TextField(null=True, blank=True)

	collection_period = models.TextField(null=True, blank=True)

	data_level = models.CharField(max_length=256, unique=False, null=True, blank=True)
	data_categories = ArrayField(models.IntegerField(), blank=True, null=True) # Note: ref to `Tag`

	@staticmethod
	def get_brand_records_by_request(request, params=None, default=None):
		user = request.user if request.user is not None and request.user.is_authenticated else None
		brand = model_utils.try_get_brand(request)
		if (brand is not None and brand.name == 'HDRN') or (brand is None and user and user.is_superuser):
			records = HDRNDataAsset.objects.all()

		if records is None:
			return default

		if not isinstance(params, dict):
			params = { }

		search = params.pop('search', None)

		query = gen_utils.parse_model_field_query(HDRNDataAsset, params, ignored_fields=['description'])
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
		ordering = ('name', )
		indexes = [
			GinIndex(name='hdrn_danm_trgm_idx', fields=['name'], opclasses=['gin_trgm_ops']),
			GinIndex(name='hdrn_dadc_arr_idx', fields=['data_categories'], opclasses=['array_ops']),
		]

	def __str__(self):
		return self.name
