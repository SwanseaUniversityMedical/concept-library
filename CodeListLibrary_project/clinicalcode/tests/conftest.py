

from clinicalcode.models import GenericEntity
from django.utils.timezone import make_aware
from datetime import datetime
import pytest
from django.contrib.auth.models import User,Group

@pytest.fixture
def generate_user():
    su_user = User.objects.create_superuser(username='superuser', password='superpassword', email=None)
    nm_user = User.objects.create_user(username='normaluser', password='normalpassword', email=None)
    ow_user = User.objects.create_user(username='owneruser', password='ownerpassword', email=None)
    gp_user = User.objects.create_user(username='groupuser', password='grouppassword', email=None)
    vgp_user = User.objects.create_user(username='viewgroupuser', password='viewgrouppassword', email=None)
    egp_user = User.objects.create_user(username='editgroupuser', password='editgrouppassword', email=None)

    users = {
        'super_user': su_user,
        'normal_user': nm_user,
        'owner_user': ow_user,
        'group_user': gp_user,
        'view_group_user': vgp_user,
        'edit_group_user': egp_user,
    }
    
    yield users
    
    # Clean up the users after the tests are finished
    for user in users.values():
        user.delete()


@pytest.fixture
def create_groups():
    permitted_group = Group.objects.create(name="permitted_group")
    forbidden_group = Group.objects.create(name="forbidden_group")
    view_group = Group.objects.create(name="view_group")
    edit_group = Group.objects.create(name="edit_group")
    
    # Yield the created groups so they can be used in tests
    yield {
        'permitted_group': permitted_group,
        'forbidden_group': forbidden_group,
        'view_group': view_group,
        'edit_group': edit_group,
    }
    
    # Clean up the groups after the tests are finished
    for group in [permitted_group, forbidden_group, view_group, edit_group]:
        group.delete()

@pytest.fixture
def generate_entity(create_groups):
    template_data = {
        "sex": "3",
        "type": "1",
        "version": 1,
        "phenoflowid": "",
        "data_sources": [
            5
        ],
        "coding_system": [],
        "agreement_date": "2012-11-23",
        "phenotype_uuid": "4",
        "event_date_range": "01/01/1999 - 01/07/2016",
        "source_reference": "https://portal.caliberresearch.org/phenotypes/archangelidi-heart-rate-6keWsw2mW2TQjDMhNAUETt",
        "concept_information": []
    }
    generate_entity = GenericEntity.objects.create(name="Test entity",
                                                   group=create_groups['permitted_group'],
                                                   template_data=template_data,updated=make_aware(datetime.now()))
    return generate_entity