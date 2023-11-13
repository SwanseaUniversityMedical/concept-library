from pytest import mark
from clinicalcode.entity_utils.permission_utils import allowed_to_create, can_user_edit_entity
import pytest
from datetime import datetime


@pytest.mark.django_db
class TestReadOnlyPermissions:

    def test_my_user(self, generate_user):
        super_user = generate_user['super_user']
        assert super_user.username == 'superuser'

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_genereic_entity(self, generate_entity, generate_user, user_type):
        generate_entity.owner = generate_user[user_type]
        generate_entity.created_by = generate_user[user_type]
        assert generate_entity.name == 'Test entity'

    @pytest.mark.parametrize('user_type', ['super_user', 'owner_user'])
    def test_users_to_edit(self, generate_user, generate_entity, user_type):
        generate_entity.owner = generate_user[user_type]
        generate_entity.created_by = generate_user[user_type]
        assert can_user_edit_entity(
            None, generate_entity, generate_user[user_type]) == False

    def test_user_not_allowed_to_create(self):
        assert allowed_to_create() == False
    
    def test_wrong_answer(self):
        assert allowed_to_create() == True
    


        
