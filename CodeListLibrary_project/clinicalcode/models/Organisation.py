from django.db import models
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.request import Request
from django.contrib.auth import get_user_model

import uuid
import datetime

from .Brand import Brand
from ..entity_utils import constants, model_utils, gen_utils

User = get_user_model()

class Organisation(models.Model):
  """
  
  """
  id = models.AutoField(primary_key=True)
  slug = models.SlugField(db_index=True, unique=True)
  name = models.CharField(max_length=250, unique=True)
  description = models.TextField(blank=True, max_length=1000)
  email = models.EmailField(null=True, blank=True)
  website = models.URLField(blank=True, null=True)

  owner = models.ForeignKey(
    User,
    on_delete=models.SET_NULL, 
    null=True, 
    default=None, 
    related_name='owned_organisations'
  )
  members = models.ManyToManyField(
    User, 
    through='OrganisationMembership',
    related_name='organisations'
  )
  brands = models.ManyToManyField(
    Brand,
    through='OrganisationAuthority',
    related_name='organisations'
  )

  created = models.DateTimeField(default=timezone.now)

  def save(self, *args, **kwargs):
    self.slug = slugify(self.name)
    super(Organisation, self).save(*args, **kwargs)

  def get_view_absolute_url(self):
    return reverse(
      'view_organisation',
      kwargs={'slug': self.slug}
    )

  def get_edit_absolute_url(self):
    return reverse(
      'edit_organisation',
      kwargs={'slug': self.slug}
    )

  def serialise_api(self):
    if self.id is None:
      return None

    return {
      'id': self.id,
      'slug': self.slug,
      'name': self.name
    }

  def __str__(self):
    return f'name={self.name}, slug={self.slug}'

class OrganisationMembership(models.Model):
  """
  
  """
  id = models.AutoField(primary_key=True)
  user = models.ForeignKey(
    User, on_delete=models.CASCADE
  )
  organisation = models.ForeignKey(
    Organisation, on_delete=models.CASCADE
  )

  role = models.IntegerField(
    choices=[(e.value, e.name) for e in constants.ORGANISATION_ROLES], 
    default=constants.ORGANISATION_ROLES.MEMBER.value
  )

  joined = models.DateTimeField(default=timezone.now, editable=False)

  def __str__(self):
    return f'user: {self.user}, org: {self.organisation}'

  @staticmethod
  def get_brand_records_by_request(request, params=None):
    # Step 1: Get the Brand from the request
    brand = model_utils.try_get_brand(request)

    members = None
    if brand is None:
      # If no specific brand, return all organisation members
      members = OrganisationMembership.objects.all()
    elif isinstance(brand, Brand):
      # Get organisations that have this brand associated through OrganisationAuthority

      members = OrganisationMembership.objects.filter(organisation__brands__id=brand.id)

    # If no members were found, return an empty queryset
    if members is None:
      return OrganisationMembership.objects.none()

     # Handle the query params and search logic
    if not isinstance(params, dict):
      params = {}

    if isinstance(request, Request) and hasattr(request, 'query_params'):
      params = {key: value for key, value in request.query_params.items()} | params
    elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
      params = {key: value for key, value in request.GET.dict().items()} | params

    # Apply additional filters based on the params (e.g., search)
    query = gen_utils.parse_model_field_query(OrganisationMembership, params)
    if query is not None:
      members = members.filter(**query)

    # Step 5: Order by id
    members = members.order_by('id')

    return members

  @staticmethod
  def get_brand_paginated_records_by_request(request, params=None):
    if not isinstance(params, dict):
      params = {}

    if isinstance(request, Request) and hasattr(request, 'query_params'):
      params = {key: value for key, value in request.query_params.items()} | params
    elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
      params = {key: value for key, value in request.GET.dict().items()} | params

    records = OrganisationMembership.get_brand_records_by_request(request, params)

    page = params.get('page', 1)
    page = max(page, 1)

    page_size = params.get('page_size', '1')
    if page_size not in constants.PAGE_RESULTS_SIZE:
      page_size = constants.PAGE_RESULTS_SIZE.get('1')
    else:
      page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

    if records is None:
      return Page(QuerySet(), 0, Paginator([], page_size, allow_empty_first_page=True))

    pagination = Paginator(records, page_size, allow_empty_first_page=True)
    try:
      page_obj = pagination.page(page)
    except EmptyPage:
      page_obj = pagination.page(pagination.num_pages)
    return page_obj

class OrganisationAuthority(models.Model):
  """
  
  """
  id = models.AutoField(primary_key=True)
  brand = models.ForeignKey(
    Brand, on_delete=models.CASCADE
  )
  organisation = models.ForeignKey(
    Organisation, on_delete=models.CASCADE
  )

  can_post = models.BooleanField(default=False)
  can_moderate = models.BooleanField(default=False)

  def __str__(self):
    return f'brand={self.brand}, org={self.organisation}'

class OrganisationInvite(models.Model):
  """
  
  """
  id = models.UUIDField( 
    primary_key = True,
    default = uuid.uuid4,
    editable = False
  )

  user = models.ForeignKey(
    User, 
    on_delete=models.SET_NULL, 
    null=True, 
    default=None, 
    related_name='organisation_invites'
  )
  organisation = models.ForeignKey(
    Organisation, 
    on_delete=models.SET_NULL, 
    null=True, 
    default=None, 
    related_name='invites'
  )

  outcome = models.IntegerField(
    choices=[(e.value, e.name) for e in constants.ORGANISATION_INVITE_STATUS], 
    default=constants.ORGANISATION_INVITE_STATUS.ACTIVE.value
  )
  sent = models.BooleanField(default=False)
  created = models.DateTimeField(default=timezone.now, editable=False)

  def is_expired(self):
    date_expired = self.created + datetime.timedelta(days=constants.INVITE_TIMEOUT)    
    return date_expired <= timezone.now()

  def is_sent(self):
    return self.sent

  def __str__(self):
    return f'user={self.user}, org={self.organisation}'
