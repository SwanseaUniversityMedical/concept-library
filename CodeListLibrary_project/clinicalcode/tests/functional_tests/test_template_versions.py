import json
import shutil
from datetime import datetime

import pytest
import requests
import yaml
from django.urls import reverse
from django.utils.timezone import make_aware
from pyconceptlibraryclient import Client
from selenium.webdriver.common.by import By

from clinicalcode.entity_utils.constants import APPROVAL_STATUS
from clinicalcode.models import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity
from clinicalcode.tests.constants.constants import API_LINK, CREATE_PHENOTYPE_TEMPLATE_PATH, \
    TEST_CREATE_PHENOTYPE_PATH, TEMPLATE_JSON_V2_PATH, NEW_FIELDS, TEMPLATE_DATA_V2


@pytest.mark.django_db
@pytest.mark.usefixtures("setup_webdriver")
class TestTemplateVersioning:

    @pytest.fixture
    def new_template_definition(self):
        """
        Pytest fixture for loading a new template definition from a JSON file.

        Returns:
            dict: A dictionary representing the new template definition.
        """
        with open(TEMPLATE_JSON_V2_PATH) as f:
            new_template = json.load(f)
        return new_template

    @pytest.fixture
    def template_v2(self, template, new_template_definition):
        """
        Pytest fixture for creating a Template instance with version 2.

        Args:
            template (Template): An existing template instance.
            new_template_definition (dict): The new template definition.

        Returns:
            Template: An instance of the Template model with version 2.
        """
        template.save()
        template.definition = new_template_definition
        template.template_version = 2
        return template

    @pytest.fixture
    def generic_entity_v2(self, create_groups, template_v2):
        """
        Pytest fixture for creating a GenericEntity instance with version 2.

        Args:
            create_groups (dict): A dictionary containing group instances.
            template_v2 (Template): An instance of the Template model with version 2.

        Returns:
            GenericEntity: An instance of the GenericEntity model with template version 2.
        """
        template_v2.save()
        generate_entity = GenericEntity(name="Test entity",
                                        author="Tester author",
                                        group=create_groups['permitted_group'],
                                        template_data=TEMPLATE_DATA_V2, updated=make_aware(datetime.now()),
                                        template=template_v2, template_version=template_v2.template_version)
        return generate_entity

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_api_data_updated(self, generate_user, user_type, template_v2, live_server):
        """
        Test whether API data is updated correctly after modifying the template version.

        Args:
            generate_user (dict): Dictionary containing user instances.
            user_type (str): Type of user for the test.
            template_v2 (Template): An instance of the Template model with version 2.
            live_server: Pytest fixture providing the live server URL.

        Returns:
            None
        """
        user = generate_user[user_type]

        template_v2.created_by = user
        template_v2.save()

        api_request = requests.get(live_server.url + API_LINK)
        api_data = api_request.json()

        assert template_v2.template_version == api_data["version_id"]

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_template_api(self, generate_user, user_type, live_server, template_v2, login):
        """
        Test the API endpoint related to template version.

        Args:
            generate_user (dict): Dictionary containing user instances.
            user_type (str): Type of user for the test.
            live_server: Pytest fixture providing the live server URL.
            template_v2 (Template): An instance of the Template model with version 2.
            login: Pytest fixture providing a login function.

        Returns:
            None
        """
        user = generate_user[user_type]

        template_v2.created_by = user
        template_v2.save()

        client = Client(
            username=user.username, password=user.username + "password",
            url=live_server.url
        )
        shutil.copy(CREATE_PHENOTYPE_TEMPLATE_PATH, TEST_CREATE_PHENOTYPE_PATH)
        client.phenotypes.create(TEST_CREATE_PHENOTYPE_PATH)

        with open(TEST_CREATE_PHENOTYPE_PATH) as stream:
            create_yaml = yaml.load(stream, Loader=yaml.FullLoader)

        assert create_yaml["template"]["version_id"] == 2

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_edit_phenotype(self, live_server, generate_entity, user_type, generate_user, login, template_v2, logout):
        """
        Test if an entity with template version 1 is updated with fields from
        template version 2 on edit.

        Args:
            live_server: Pytest fixture providing the live server URL.
            generate_entity (GenericEntity): An instance of the GenericEntity model.
            user_type (str): Type of user for the test.
            generate_user (dict): Dictionary containing user instances.
            login: Pytest fixture providing a login function.
            template_v2 (Template): An instance of the Template model with version 2.
            logout: Pytest fixture providing a logout function.

        Returns:
            None
        """
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")
        generate_entity.owner = user
        generate_entity.created_by = user
        generate_entity.save()
        template_v2.created_by = user
        template_v2.save()

        self.driver.get(live_server.url + f"/phenotypes/{generate_entity.id}/version/2/detail/")
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        titles = self.driver.find_elements(By.CLASS_NAME, "detailed-input-group__title")
        title_texts = [title.text.replace("\n*", "") for title in titles]

        logout(self.driver)

        assert set(NEW_FIELDS) <= set(title_texts)

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_export_json(self, live_server, generate_user, generic_entity_v2, user_type, login, logout):
        """
        Test exporting entity data in JSON format is reflected for entity created using template version 2.

        Args:
            live_server: Pytest fixture providing the live server URL.
            generate_user (dict): Dictionary containing user instances.
            generic_entity_v2 (GenericEntity): An instance of the GenericEntity model with version 2.
            user_type (str): Type of user for the test.
            login: Pytest fixture providing a login function.
            logout: Pytest fixture providing a logout function.

        Returns:
            None
        """
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")
        generic_entity_v2.owner = user
        generic_entity_v2.created_by = user
        generic_entity_v2.save()

        self.driver.get(live_server.url + f"/api/v1/phenotypes/{generic_entity_v2.id}/version/3/detail/?format=json")
        pre = self.driver.find_element(By.TAG_NAME, "pre").text
        phenotype_data = json.loads(pre)[0]

        logout(self.driver)

        assert phenotype_data["template"]["version_id"] == 2

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_entity_published(self, live_server, generate_user, login, logout, user_type, generic_entity_v2):
        """
        Test if the publishing of a GenericEntity with version 2 reflects in the home page statistics.

        Args:
            live_server: Pytest fixture providing the live server URL.
            generate_user (dict): Dictionary containing user instances.
            login: Pytest fixture providing a login function.
            logout: Pytest fixture providing a logout function.
            user_type (str): Type of user for the test.
            generic_entity_v2 (GenericEntity): An instance of the GenericEntity model with version 2.

       Returns:
           None
       """
        def get_publisheed_entity_count():
            self.driver.get(live_server.url)
            count = self.driver.find_element(By.ID, "entity-counter").text
            return int(count)

        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        init_count = get_publisheed_entity_count()

        generic_entity_v2.owner = user
        generic_entity_v2.created_by = user
        generic_entity_v2.save()

        published_entity = PublishedGenericEntity(entity=generic_entity_v2, entity_history_id=4, moderator_id=user.id,
                                                  created_by_id=generic_entity_v2.created_by.id,
                                                  approval_status=APPROVAL_STATUS.APPROVED)
        published_entity.save()
        self.driver.get(live_server + reverse("run_homepage_statistics"))

        final_count = get_publisheed_entity_count()
        assert final_count == init_count + 1

# pytest -v -s clinicalcode/tests/functional_tests/test_template_versions.py
