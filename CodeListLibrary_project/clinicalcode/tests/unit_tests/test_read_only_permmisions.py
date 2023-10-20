from operator import ge
import pytest
from datetime import datetime



@pytest.mark.django_db
class ReadOnlyPermissionsTest:
    def test_my_user(self,generate_user):
        super_user = generate_user['super_user']
        assert super_user.username == "superuser"

    @pytest.mark.parametrize("user_type", ["super_user"])    
    def test_genereic_entity(self,generate_entity,generate_user,user_type):
        
        generate_entity.owner = generate_user[user_type]
        generate_entity.created_by = generate_user[user_type]
        print(generate_entity.name)
        assert generate_entity.name == "Test entity"
    
     def test_owner_not_allowed_to_edit(self,generate_user,generate_entity):
        assert can_user_edit_entity(None,generate_entity,generate_user['owner_user']) == False

    

    
