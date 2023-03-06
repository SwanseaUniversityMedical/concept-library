from django.conf import settings
from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension, BtreeGinExtension

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clinicalcode', '0078_remove_historicaltemplate_entity_count_and_more'),
    ]

    operations = [
        TrigramExtension(),
        BtreeGinExtension(),
    ]
