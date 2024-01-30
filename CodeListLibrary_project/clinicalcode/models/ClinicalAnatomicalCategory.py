from django.db import models
from django.apps import apps
from django_postgresql_dag.models import node_factory, edge_factory

class ClinicalAnatomicalCategoryEdge(edge_factory('ClinicalAnatomicalCategoryNode', concrete=False)):
  name = models.CharField(max_length=1024, unique=True)

  def __str__(self):
      return self.name

  def save(self, *args, **kwargs):
      self.name = f'{self.parent.name} {self.child.name}'
      super().save(*args, **kwargs)

class ClinicalAnatomicalCategoryNode(node_factory(ClinicalAnatomicalCategoryEdge)):
    name = models.CharField(max_length=510, unique=True)
    atlas_id = models.IntegerField(blank=True, null=True, unique=True)

    def __str__(self):
        return self.name
