import pytest
from django.contrib.auth.models import User

@pytest.fixture
def test_users():
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
