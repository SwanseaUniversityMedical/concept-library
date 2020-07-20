from django.db import models
from .CodingSystem import CodingSystem
from clinicalcode.models.Operator import Operator


class CodingSystemFilter(models.Model):

	DATA_TYPE_STRING = "string"
	DATA_TYPE_INTEGER = "integer"
	DATA_TYPE_DOUBLE = "double"
	DATA_TYPE_DATE = "date"
	DATA_TYPE_TIME = "time"
	DATA_TYPE_DATETIME = "datetime"
	DATA_TYPE_BOOLEAN = "boolean"

	DATA_TYPES = (
		(DATA_TYPE_STRING, "string"),
		(DATA_TYPE_INTEGER, "integer"),
		(DATA_TYPE_DOUBLE, "double"),
		(DATA_TYPE_DATE, "date"),
		(DATA_TYPE_TIME, "time"),
		(DATA_TYPE_DATETIME, "datetime"),
		(DATA_TYPE_BOOLEAN, "boolean"),
	)

	coding_system_filter_id = models.AutoField(primary_key=True)
	id = models.CharField(max_length=50)
	label = models.CharField(max_length=50)
	type = models.CharField(choices=DATA_TYPES, max_length=20)
	operators = models.ManyToManyField(Operator)
	coding_system = models.ForeignKey(CodingSystem, blank=True, null=True)

	def __str__(self):
		return self.id

	