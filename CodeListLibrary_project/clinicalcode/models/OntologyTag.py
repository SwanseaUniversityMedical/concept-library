from django.apps import apps
from django.db import models, transaction
from django_postgresql_dag.models import node_factory, edge_factory

from .CodingSystem import CodingSystem
from ..entity_utils import gen_utils, constants

class OntologyTagEdge(edge_factory('OntologyTag', concrete=False)):
  name = models.CharField(max_length=2048, unique=False)

  def __str__(self):
      return self.name

  def save(self, *args, **kwargs):
      self.name = f'{self.parent.name} {self.child.name}'
      super().save(*args, **kwargs)

class OntologyTag(node_factory(OntologyTagEdge)):
    name = models.CharField(max_length=1024, unique=False)
    type_id = models.IntegerField(choices=[(e.name, e.value) for e in constants.ONTOLOGY_TYPES])
    atlas_id = models.IntegerField(blank=True, null=True, unique=False)
    properties = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name

    @transaction.atomic
    def save(self, *args, **kwargs):
        internal_type = self.type_id

        if internal_type == constants.ONTOLOGY_TYPES.CLINICAL_DISEASE:
            code_id = self.__validate_disease_code_id(self.properties)
            if isinstance(code_id, int):
                self.properties.update({ 'code_id': code_id })

        super().save(*args, **kwargs)

    def __validate_disease_code_id(self, properties):
        if not isinstance(properties, dict):
            return None

        try:
            desired_code = properties.get('code')
            desired_system_id = gen_utils.parse_int(properties.get('coding_system_id'), None)

            if not isinstance(desired_code, str) or not isinstance(desired_system_id, int):
                return None

            desired_system = CodingSystem.objects.filter(pk__eq=desired_system_id)
            desired_system = desired_system.first() if desired_system.exists() else None

            if desired_system is None:
                return None

            comparators = [ desired_code.lower(), desired_code.replace('.', '').lower() ]
            table_name = desired_system.table_name
            model_name = desired_system.table_name.replace('clinicalcode_', '')
            codes_name = desired_system.code_column_name.lower()

            query = """
                select *
                    from public.%(table_name)s
                    where lower(%(column_name)s);

                """ % { 'table_name': table_name, 'column_name': codes_name }

            codes = apps.get_model(app_label='clinicalcode', model_name=model_name)
            code = codes.objects.raw(query + ' = ANY(%(values)s::text[])', { 'values': comparators })
        except:
            code = None
        finally:
            if code is None or not code.exists():
                return None
            return code.first().pk
