from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

import uuid
import datetime

from .Brand import Brand
from ..entity_utils import constants

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
