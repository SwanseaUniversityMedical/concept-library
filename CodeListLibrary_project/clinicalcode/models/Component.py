'''
    ---------------------------------------------------------------------------
    COMPONENT MODEL

    Model for the concept components.
    ---------------------------------------------------------------------------
'''

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

from .Concept import Concept, HistoricalConcept
from .TimeStampedModel import TimeStampedModel


class Component(TimeStampedModel):
    '''
        Component of a concept.
        Each component type allows the user to define a set of codes for a
        concept in a different way. These codes can be included in or removed
        from the list that constitutes the concept.
    '''
    LOGICAL_TYPE_INCLUSION = 1
    LOGICAL_TYPE_EXCLUSION = 2

    LOGICAL_TYPES = (
        (LOGICAL_TYPE_INCLUSION, 'Add codes'),
        (LOGICAL_TYPE_EXCLUSION, 'Remove codes'),
    )

    COMPONENT_TYPE_CONCEPT = 1
    COMPONENT_TYPE_QUERY_BUILDER = 2
    COMPONENT_TYPE_EXPRESSION = 3
    COMPONENT_TYPE_EXPRESSION_SELECT = 4
    COMPONENT_TYPE_EXPRESSION_PH_SEARCH = 5
    COMPONENT_TYPE_EXPRESSION_PH_FILE = 6
    COMPONENT_TYPE_EXPRESSION_PH_POINTER = 7

    COMPONENT_TYPES = (
        (COMPONENT_TYPE_CONCEPT, 'Concept'),
        (COMPONENT_TYPE_QUERY_BUILDER, 'Query Builder'),
        (COMPONENT_TYPE_EXPRESSION, 'Expression'),
        (COMPONENT_TYPE_EXPRESSION_SELECT, 'Select/Import'),
        (COMPONENT_TYPE_EXPRESSION_PH_SEARCH, 'Searchterm'),
        (COMPONENT_TYPE_EXPRESSION_PH_FILE, 'File Upload'),
        (COMPONENT_TYPE_EXPRESSION_PH_POINTER, 'Concept'),
    )

    # Only used for rulesets
    source = models.CharField(max_length=250, blank=True, null=True)
    used_wildcard = models.BooleanField(default=False)
    used_description = models.BooleanField(default=False)
    was_wildcard_sensitive = models.BooleanField(default=False)

    comment = models.TextField()
    component_type = models.IntegerField(choices=COMPONENT_TYPES)
    concept = models.ForeignKey(Concept,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)

    # The ID of a concept (if this component is another concept). Otherwise null.
    concept_ref = models.ForeignKey(Concept,
                                    on_delete=models.SET_NULL,
                                    blank=True,
                                    null=True,
                                    related_name="concept_ref")
    concept_ref_history = models.ForeignKey(HistoricalConcept,
                                            on_delete=models.SET_NULL,
                                            blank=True,
                                            null=True,
                                            related_name="+")
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="components_created")
    logical_type = models.IntegerField(choices=LOGICAL_TYPES,
                                       default=LOGICAL_TYPE_INCLUSION)
    modified_by = models.ForeignKey(User,
                                    on_delete=models.SET_NULL,
                                    null=True,
                                    related_name="components_modified")
    name = models.CharField(max_length=250)
    history = HistoricalRecords()

    class Meta:
        ordering = ('created', )

    def __str__(self):
        return self.name
