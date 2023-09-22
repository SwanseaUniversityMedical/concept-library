from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import models
from PIL import Image

from ..entity_utils import constants
from ..entity_utils import image_utils

def image_path(instance, filename):
    '''
        Will be uuid 
    '''
    return 'entity/%s_%s' % (instance.name, image_utils.get_hash(instance.image)) 

def validate_image(image):
    '''
    
    '''
    if image.file.size > constants.MAX_IMAGE_SIZE:
        raise ValidationError('Exceeds max image size: %s' % constants.MAX_IMAGE_SIZE)

class GenericEntityImage(models.Model):
    '''
    
    '''
    id = models.AutoField(primary_key=True)

    entity_owner = models.ForeignKey('clinicalcode.GenericEntity', on_delete=models.SET_NULL, null=True, blank=True, related_name='images')
    name = models.CharField(max_length=250)
    image = models.ImageField(upload_to=image_path, validators=[validate_image])

    ''' Creation information '''
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="uploaded_images")

    is_deleted = models.BooleanField(null=True, default=False)
    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_images")

    def save(self, *args, **kwargs):
        instance = super(GenericEntityImage, self).save(*args, **kwargs)
        image = Image.open(instance.image.path)
        image.save(instance.image.path, quality=constants.IMAGE_COMPRESSION_QUALITY, optimize=True)
        return instance

    def __str__(self):
        return self.name
