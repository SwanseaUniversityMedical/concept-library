from django.db import models
from django.contrib.auth.models import Group, User

from ..entity_utils import constants

class ContentPermission(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    world_access = models.IntegerField(choices=[(e.name, e.value) for e in constants.GROUP_PERMISSIONS], default=constants.GROUP_PERMISSIONS.NONE)

    class Meta:
        ordering = ('id', )

    def __str__(self):
        ownership = filter(None, [
            f'owner: {self.owner.username}' if self.owner is not None else None,
            f'group: {self.group.name}' if self.group is not None else None
        ])

        ownership = (', ').join(ownership) if any(ownership) else 'NULL'
        return f'ContentPermission<{ownership}>'
