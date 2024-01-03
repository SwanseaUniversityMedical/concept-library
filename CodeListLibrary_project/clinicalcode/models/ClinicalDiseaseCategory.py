from django.db import models
from django.apps import apps
from django_postgresql_dag.models import node_factory, edge_factory

from .CodingSystem import CodingSystem

class ClinicalDiseaseCategoryEdge(edge_factory('ClinicalDiseaseCategoryNode', concrete=False)):
  name = models.CharField(max_length=1024, unique=True)

  def __str__(self):
      return self.name

  def save(self, *args, **kwargs):
      self.name = f'{self.parent.name} {self.child.name}'
      super().save(*args, **kwargs)

class ClinicalDiseaseCategoryNode(node_factory(ClinicalDiseaseCategoryEdge)):
    name = models.CharField(max_length=510)
    code = models.CharField(max_length=255, null=True, blank=True)
    code_id = models.IntegerField(null=True, blank=True)
    coding_system = models.ForeignKey(CodingSystem, on_delete=models.SET_NULL, related_name='disease_categories', null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        desired_code = self.code
        desired_system = self.coding_system

        if desired_code is not None and desired_system is not None:
            try:
                comparators = [ desired_code, desired_code.replace('.', '') ]

                table_name = desired_system.table_name
                model_name = desired_system.table_name.replace('clinicalcode_', '')
                codes_name = desired_system.code_column_name.lower()

                query = """
                    select *
                      from public.%(table_name)s
                     where lower(%(column_name)s)""" % { 'table_name': table_name, 'column_name': codes_name }

                codes = apps.get_model(app_label='clinicalcode', model_name=model_name)
                code = codes.objects.raw(query + ' = ANY(%(values)s::text[])', { 'values': comparators })
                code = code.first() if code.exists() else None
            except:
                self.code_id = None
                pass
            else:
                if code is not None:
                    self.code_id = code.pk

        super().save(*args, **kwargs)
