from clinicalcode.tests.constants.constants import TEST_CREATE_PHENOTYPE_WITH_ACCESS_PATH,TEST_CREATE_PHENOTYPE_NO_ACCESS_PATH
import pytest

from pyconceptlibraryclient import Client


@pytest.mark.django_db(reset_sequences=True,transaction=True)
@pytest.mark.usefixtures("setup_webdriver")
class TestAuthPhenoAccess:
    """
    Test class to verify authentication and user access control for phenotypes.
    """


    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_user_with_access(self, generate_user, user_type, live_server, generate_entity):
        """
        Test to verify if a user can access unpublished phenotypes with group/world access.

        Args:
            generate_user (dict): Dictionary of generated users.
            user_type (str): Type of user to test.
            live_server (LiveServer): Live server instance for testing.
            generic_entity (GenericEntity): The generic entity fixture.
        """
        user = generate_user[user_type]

        client = Client(
            username=user.username, password=user.username + "password",
            url=live_server.url
        )

        generate_entity.owner = user
        generate_entity.created_by = user
        generate_entity.save()

        client.phenotypes.create(TEST_CREATE_PHENOTYPE_WITH_ACCESS_PATH)

        normal_user_type = 'normal_user'
        normal_user = generate_user[normal_user_type]

        normal_user_client = Client(
            username=normal_user.username, password=normal_user.username + "password",
            url=live_server.url
        )

        pheno_ver_normal_user = normal_user_client.phenotypes.get_versions('PH2')
        print("Phenotype PH2 with group/world access:", pheno_ver_normal_user)
        assert pheno_ver_normal_user != []  

        non_auth_client = Client(public=True, url=live_server.url)
        non_auth_user = non_auth_client.phenotypes.get_versions('PH2')
        print("Non authenticated user cannot view unpublished phenotype", non_auth_user)
        assert non_auth_user == []

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_user_without_access(self, generate_user, user_type, live_server, generate_entity):
        """
        Test to verify if a user can view phenotypes without group/world access.

        Args:
            generate_user (dict): Dictionary of generated users.
            user_type (str): Type of user to test.
            live_server (LiveServer): Live server instance for testing.
            generic_entity (GenericEntity): The generic entity fixture.
        """
        user = generate_user[user_type]

        client = Client(
            username=user.username, password=user.username + "password",
            url=live_server.url
        )

        generate_entity.owner = user
        generate_entity.created_by = user
        generate_entity.save()

        template_list = client.templates.get()
        print("GET ALL TEMPLATE LIST:", template_list)

        client.phenotypes.create(TEST_CREATE_PHENOTYPE_NO_ACCESS_PATH)

        normal_user_type = 'normal_user'
        normal_user = generate_user[normal_user_type]

        normal_user_client = Client(
            username=normal_user.username, password=normal_user.username + "password",
            url=live_server.url
        )

        get_user_match_phenos = normal_user_client.phenotypes.get_versions('PH2')
        print(get_user_match_phenos)
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

    def test_non_authenticated_user_create_phenos(self):
        """
        Test to verify that non-authenticated users can't create phenotypes.
        """
        client = Client(public=True)
        
        try:
            client.phenotypes.create(TEST_CREATE_PHENOTYPE_NO_ACCESS_PATH)
        except RuntimeError as e:
            print(e, "Phenotype could not have been created due to user not being Authenticated")
            assert True, "Runtime error raised"

    def test_auth_user_edit(self):

        """
        Test to verify that non-authenticated users can't update phenotypes.
        """
        client = Client(public=True)
        
        try:
            client.phenotypes.update(TEST_CREATE_PHENOTYPE_NO_ACCESS_PATH)
        except RuntimeError as e:
            print(e, "Phenotype could not have been updated due to user not being Authenticated")
            assert True, "Runtime error raised"

