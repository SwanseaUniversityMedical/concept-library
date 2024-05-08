import json
from datetime import datetime
from pathlib import Path

import pytest
from django.utils.timezone import make_aware
from pyconceptlibraryclient import Client

from clinicalcode.models import GenericEntity
from clinicalcode.entity_utils.constants import APPROVAL_STATUS, WORLD_ACCESS_PERMISSIONS

# Importing relevant modules and classes

@pytest.mark.django_db
@pytest.mark.usefixtures("setup_webdriver")
class TestAuthPhenoAccess:

    """
    Test class to verify authentication and user access control for phenotypes.
    """

    @pytest.fixture
    def template_definition(self):
        """
        Fixture to load template definition from JSON file.
        """
        with open('../constants/test_template.json') as f:
            new_template = json.load(f)
        return new_template
    
    @pytest.fixture
    def generic_entity(self, create_groups, template):
        """
        Fixture to create a generic entity with specified attributes.
        """
        with open('../constants/test_template.json') as f:
            template_definition = json.load(f)
        template.definition = template_definition 
        template.save()
        
        generate_entity = GenericEntity(
            name="Test entity",
            author="Tester author",
            group=create_groups['permitted_group'],
            updated=make_aware(datetime.now()),
            template=template,
            publish_status=APPROVAL_STATUS.APPROVED
        )

        generate_entity.world_access = WORLD_ACCESS_PERMISSIONS.NONE
        return generate_entity
    

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_user_with_access(self, generate_user, user_type, live_server, generic_entity):
        """
        Test to verify if a user can access phenotypes with group/world access.
        """
        user = generate_user[user_type]

        client = Client(
            username=user.username, password=user.username + "password",
            url=live_server.url
        )

        generic_entity.owner = user
        generic_entity.created_by = user
        generic_entity.save()

        template_list = client.templates.get()
        print("Available template list:", template_list)

        client.phenotypes.create('../constants/test_create_phenotype_w_access.yaml')

        normal_user_type = 'normal_user'
        normal_user = generate_user[normal_user_type]

        normal_user_client = Client(
            username=normal_user.username, password=normal_user.username + "password",
            url=live_server.url
        )

        pheno_ver_normal_user = normal_user_client.phenotypes.get_versions('PH2')
        print("Phenotype PH2 with group/world access:", pheno_ver_normal_user)
        assert pheno_ver_normal_user != []             
    
    
    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_user_without_access(self, generate_user, user_type, live_server, generic_entity):
        """
        Test to verify if a user can view phenotypes without group/world access.
        """
        user = generate_user[user_type]

        client = Client(
            username=user.username, password=user.username + "password",
            url=live_server.url
        )

        generic_entity.owner = user
        generic_entity.created_by = user
        generic_entity.save()

        template_list = client.templates.get()
        print("GET ALL TEMPLATE LIST:", template_list)

        client.phenotypes.create('../constants/test_create_pheno_no_access.yaml')

        normal_user_type = 'normal_user'
        normal_user = generate_user[normal_user_type]

        normal_user_client = Client(
            username=normal_user.username, password=normal_user.username + "password",
            url=live_server.url
        )

        get_user_match_phenos = normal_user_client.phenotypes.get_versions('PH2')
        print("User can't view phenotype without world/group access:", get_user_match_phenos)
        assert get_user_match_phenos == []


    def test_non_authenticated_user_view_published_phenos(self):
        """
        Test to verify that non-authenticated users can view published phenotypes.
        """
        client = Client(public=True)

        get_user_match_phenos = client.phenotypes.get_versions('PH1')
        print(get_user_match_phenos)
        print("User can view published phenotypes:", get_user_match_phenos)
        assert get_user_match_phenos != []
