"""Multi-site branded domain targets."""

from django.db import models
from django.core.cache import cache
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

from .TimeStampedModel import TimeStampedModel

class Brand(TimeStampedModel):
    """Domain Brand specifying site appearance and behaviour variation."""

    '''Fields'''
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


    '''Static methods'''
    @staticmethod
    def all_instances(cached=True):
        """
            Gets all Brand instances from this model

            Args:
                cached (bool): optionally specify whether to retrieve the cached instances; defaults to `True`

            Returns:
                A (QuerySet) containing all Brands
        """
        if not cached:
            return Brand.objects.all()

        all_brands = cache.get('brands_all__cache')
        if all_brands is None:
            all_brands = Brand.objects.all()
            cache.set('brands_all__cache', all_brands, 3600)
        return all_brands

    @staticmethod
    def all_names(cached=True):
        """
            Gets a list of all Brand name targets

            Args:
                cached (bool): optionally specify whether to retrieve the cached name list; defaults to `True`

            Returns:
                A (list) containing the names of each Brand instance _assoc._ with this model
        """
        if not cached:
            return [x.upper() for x in Brand.objects.all().values_list('name', flat=True)]

        named_brands = cache.get('brands_names__cache')
        if named_brands is None:
            named_brands = [x.upper() for x in Brand.objects.all().values_list('name', flat=True)]
            cache.set('brands_names__cache', named_brands, 3600)
        return named_brands

    @staticmethod
    def all_vis_rules(cached=True):
        """
            Resolves all Brand content visibility rules

            Note:
                - Beware that not all Brands are _assoc._ with content visibility rules;
                - Brands that do not specify content visibility rules will not be present in the resulting dict.

            Args:
                cached (bool): optionally specify whether to retrieve the cached resultset; defaults to `True`

            Returns:
                A (dict) containing key-value pairs in which the key describes the Brand name, and the value describes the content visibility rules _assoc._ with that Brand.
        """
        vis_rules = cache.get('brands_vis-rules__cache') if cached else None
        if vis_rules is None:
            brands = Brand.all_instances(cached=cached)
            vis_rules = [ x.get_vis_rules() for x in brands ]
            vis_rules = { brand.name: rule for brand, rule in zip(dict(brands, vis_rules)).items() }

            if cached:
                cache.set('brands_vis-rules__cache', vis_rules, 3600)

        return vis_rules


    '''Instance methods'''
    def get_vis_rules(self, cached=False, default=None):
        """
            Attempts to resolve this Brand's `content-visibility` override attribute

            Note:
                A Brand's `content-visibility` may be one of: <br/>

                a.) A "_falsy_" value, _e.g._ a `None` or `False` value, in which:
                    - Falsy values specifies that no `content-visibility` rules should be applied;
                    - _i.e._ that all content should be visible.

                b.) Or, a `Literal` `str` value of either (a) `self` or (b) `allow_null`, such that:
                    - `self` → only content created for this `Brand` should be visible;
                    - `allow_null` → the `self` rule but allows all content not associated with a particular `Brand` to be rendered alongside it.

                c.) Or, a `list[int]` describing the Brand IDs that should be visible on this domain alongside itself;

                d.) Or, a `dict[str, Any]` with the following key-value pairs:
                    - `allow_null` → optionally specifies whether content not associated with a particular `Brand` should be visibile;
                    - `allowed_brands` → optionally specifies the Brand IDs whose content should also be visible on this domain.

            Args:
                cached (bool): optionally specify whether to retrieve the cached resultset; defaults to `False`
                default (Any): optionally specify the default return value if the `content-visibility` attr is undefined; defaults to `None`

            Returns:
                This Brand's `content-visibility` rule if applicable, otherwise returns the specified `default` value
        """
        # Handle case where instance has yet to be saved
        if self.id is None:
            return default

        # Build vis rules
        cache_key = f'brands_vis-rules__{self.name}__cache' if cached else None
        vis_rules = cache.get(cache_key) if cached else None
        if vis_rules is not None:
            return vis_rules.get('value')

        vis_rules = getattr(self, 'overrides')
        vis_rules = vis_rules.get('content-visibility') if isinstance(vis_rules, dict) else None
        if isinstance(vis_rules, bool) and vis_rules:
            vis_rules = { 'ids': [self.id], 'allow_null': False }
        if isinstance(vis_rules, str):
            vis_rules = vis_rules.lower()
            if vis_rules in ('self', 'allow_null'):
                vis_rules = {
                    'ids': [self.id],
                    'allow_null': vis_rules == 'allow_null'
                }
            else:
                vis_rules = default
        elif isinstance(vis_rules, list):
            if self.id not in vis_rules:
                vis_rules.insert(0, self.id)

            vis_rules = { 'ids': [x for x in vis_rules if isinstance(x, int)], 'allow_null': False }
        elif isinstance(vis_rules, dict):
            allow_null = vis_rules.get('allow_null')
            allowed_brands = vis_rules.get('allowed_brands')
            if isinstance(allow_null, bool) or isinstance(allowed_brands, list):
                allow_null = False if not isinstance(allow_null, bool) else allow_null
                allowed_brands = [] if not allowed_brands else allowed_brands

                if self.id not in allowed_brands:
                    allowed_brands.insert(0, self.id)

                vis_rules = {
                    'ids': [x for x in allowed_brands if isinstance(x, int)],
                    'allow_null': allow_null
                }
            else:
                vis_rules = default
        elif isinstance(vis_rules, (None, bool)) and not vis_rules:
            vis_rules = default

        if cached:
            cache.set(cache_key, { 'value': vis_rules }, 3600)

        return vis_rules


    '''Metadata'''
    class Meta:
        ordering = ('name', )


    '''Dunder methods'''
    def __str__(self):
        return self.name
