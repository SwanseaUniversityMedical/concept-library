from django.core.management.base import BaseCommand

import os
import glob
import json

from ...models.ClinicalConcept import ClinicalConcept
from ...models.ClinicalConcept import ClinicalRuleset

from ...models.CodingSystem import CodingSystem
from ...models.Concept import Concept
from ...models.Component import Component
from ...models.CodeList import CodeList
from ...models.Code import Code

class Command(BaseCommand):
    IS_DEBUG = True

    help = 'Example usage of historical models'

    def __get_log_style(self, style):
        if not isinstance(style, str):
            return style

        style = style.upper()
        if style == 'SUCCESS':
            return self.style.SUCCESS
        elif style == 'NOTICE':
            return self.style.NOTICE
        elif style == 'WARNING':
            return self.style.WARNING
        elif style == 'ERROR':
            return self.style.ERROR
        return self.style.SUCCESS

    def __log(self, message, style='SUCCESS'):
        style = self.__get_log_style(style)
        self.stdout.write(style(message))

    def __migrate_concept(self, *args, **kwargs):
        ids = kwargs.get('ids') or 'ALL'
        ids = ids.upper().split(',')
        if ids[0] == 'ALL':
            ids = list(Concept.objects.all().values_list('id', flat=True))
        
        self.__log(f'Migrating Concepts #{len(ids)}')

    def __test_historical_records(self, *args, **kwargs):
        # Create Concept
        self.__log('Create Concept')
        clin_concept = ClinicalConcept(
            name='COVID-19 with rules',
            coding_system=CodingSystem.objects.get(id=4)
        )
        clin_concept.save()
        self.__log(f'Created initial: ClinicalConcept<id={clin_concept.entity_id}, version={clin_concept.version_id}>', style=self.style.MIGRATE_LABEL)
        
        # Add a rule
        clin_ruleset = ClinicalRuleset(name='Some ruleset')
        clin_ruleset.save()
        clin_concept.rulesets.add(clin_ruleset)

        # Update the concept for some reason
        self.__log('Update Concept')
        clin_concept.name = 'COVID-19 with change'
        clin_concept.save()
        self.__log(f'Diff: {clin_concept.history.get(version_id=1).get_delta(clin_concept)}', style=self.style.MIGRATE_HEADING)

        # Remove the ruleset(s) and update the Concept
        self.__log('Remove Rules')
        clin_concept.name = 'COVID-19 with removed rules'
        clin_concept.coding_system = CodingSystem.objects.get(id=7)
        clin_concept.save()
        clin_concept.rulesets.clear()
        self.__log(f'Diff: {clin_concept.history.get(version_id=2).get_delta(clin_concept)}', style=self.style.MIGRATE_HEADING)

        self.__log('Result:')
        self.__log(f'1. ClinicalConcept<id={clin_concept.entity_id}, version={clin_concept.version_id}>', style=self.style.MIGRATE_LABEL)
        self.__log(f'2. Historical records: {list(clin_concept.history.all())}', style=self.style.MIGRATE_LABEL)

    def add_arguments(self, parser):
        if not self.IS_DEBUG:
            parser.add_argument('-i', '--ids', type=str, help='Only migrate a specific instance, or instances (using a comma delimiter)')

    def handle(self, *args, **kwargs):
        if not self.IS_DEBUG:
            self.__migrate_concept(*args, **kwargs)
            return
        self.__test_historical_records(*args, **kwargs)
