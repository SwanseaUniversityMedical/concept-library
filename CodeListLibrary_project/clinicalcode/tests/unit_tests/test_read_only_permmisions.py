import pytest
from datetime import datetime
from django.contrib.auth.models import User, Group



@pytest.mark.django_db
class TestUsers:
    def test_my_user(self,test_users):
        super_user = test_users['super_user']
        assert super_user.username == "superuser"