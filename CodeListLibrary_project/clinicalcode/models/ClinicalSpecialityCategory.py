from django.db import models
from django.apps import apps
from django_postgresql_dag.models import node_factory, edge_factory

class ClinicalSpecialityCategoryEdge(edge_factory('ClinicalSpecialityCategoryNode', concrete=False)):
  name = models.CharField(max_length=1024, unique=True)

  def __str__(self):
      return self.name

  def save(self, *args, **kwargs):
      self.name = f'{self.parent.name} {self.child.name}'
      super().save(*args, **kwargs)

class ClinicalSpecialityCategoryNode(node_factory(ClinicalSpecialityCategoryEdge)):
    name = models.CharField(max_length=510, unique=True)

    def __str__(self):
        return self.name
