from django.db import models

class Operator(models.Model):
    description = models.CharField(max_length=20)

    def __str__(self):
        return self.description
