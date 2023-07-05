from django.core.management.base import BaseCommand

import os
import glob
import json

from ...models.CodingSystem import CodingSystem
from ...models.Brand import Brand

class Command(BaseCommand):
    help = 'Updates the legacy models to incl. the changes to brands & coding system per the new specification'

    DEFAULT_DIR = 'data/brands'
    FILTER_UPD = {
        'ICD10 codes': 'effective_to is null',
        'OPCS4 codes': 'effective_to is null',
    }
    FIELD_MAP = {
        'menu': 'about_menu',
        'footer': 'footer_images',
    }

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

    def __try_load_file(self, file):
        try:
            with open(file) as f:
                data = json.load(f)
                return data
        except Exception as e:
            self.__log(f'Error when attempting to load file <{file}>', style='ERROR')
            self.__log(str(e), style='ERROR')
        return None

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str, help='Location of Menu / Footer files directory relative to manage.py')

    def handle(self, *args, **kwargs):
        # update coding system filters
        for name, filter_value in self.FILTER_UPD.items():
            coding_system = CodingSystem.objects.filter(name=name)
            if not coding_system.exists():
                self.__log(f'Unable to find coding system with name <{name}>', style='WARNING')

            coding_system = coding_system.first()
            coding_system.filter = filter_value
            coding_system.save()

        self.__log('Finished executing CodingSystem update')

        # update brand components
        directory = kwargs.get('file')
        directory = os.path.join(
            os.path.abspath(os.path.dirname('manage.py')),
            directory if directory is not None else self.DEFAULT_DIR
        )

        for file in glob.glob(os.path.join(directory, '**/*.json')):
            name = os.path.splitext(os.path.basename(file))[0]
            brand = Brand.objects.filter(name=name)
            if not brand.exists():
                continue

            brand = brand.first()
            parent = os.path.basename(os.path.dirname(file)).lower()
            field = self.FIELD_MAP.get(parent) if parent in self.FIELD_MAP else None
            if field is None:
                continue

            data = self.__try_load_file(file)
            if data is None:
                continue

            setattr(brand, field, data)
            brand.save()

        self.__log('Finished executing Brand update')
