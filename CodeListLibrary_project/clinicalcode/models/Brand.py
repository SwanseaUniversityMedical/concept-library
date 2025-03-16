from django.db import models
from django.core.cache import cache
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

from .TimeStampedModel import TimeStampedModel

class Brand(TimeStampedModel):
    id = models.AutoField(primary_key=True)

    # Brand metadata
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(max_length=1000, blank=True, null=True)

    # Brand site modifiers
    #   - title: modifies `<title />`-related content
    #   - description: modifies the `<meta name="description"/>` content
    #
    site_title = models.CharField(max_length=50, blank=True, null=True)
    site_description = models.CharField(max_length=160, blank=True, null=True)

    # Brand page & logo appearance
    logo_path = models.CharField(max_length=250)
    index_path = models.CharField(max_length=250, blank=True, null=True)

    # Brand administration
    admins = models.ManyToManyField(User, related_name='administered_brands')

    # Brand overrides
    #   - e.g. entity name override ('Concept' instead of 'Phenotype' _etc_ for HDRN brand)
    overrides = models.JSONField(blank=True, null=True)

    # Brand organisation controls
    org_user_managed = models.BooleanField(default=False)

    # Brand menu targets
    about_menu = models.JSONField(blank=True, null=True)
    allowed_tabs = models.JSONField(blank=True, null=True)
    footer_images = models.JSONField(blank=True, null=True)
    collections_excluded_from_filters = ArrayField(models.IntegerField(), blank=True, null=True)

    @classmethod
    def all_cached(self):
        """Cached QuerySet list of all Brands"""
        all_brands = cache.get('brands_all__cache')
        if all_brands is None:
            all_brands = Brand.objects.all()
            cache.set('brands_all__cache', all_brands, 3600)
        return all_brands

    @classmethod
    def names_list_cached(self):
        """Cached list of all Brand name targets"""
        named_brands = cache.get('brands_names__cache')
        if named_brands is None:
            named_brands = [x.upper() for x in Brand.objects.all().values_list('name', flat=True)]
            cache.set('brands_names__cache', named_brands, 3600)
        return named_brands

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name
