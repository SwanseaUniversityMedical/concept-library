import json
import os
import time
import shutil

import pytest
import requests
import yaml
from pyconceptlibraryclient import Client
from selenium.webdriver.common.by import By
from clinicalcode.models.Template import Template

from clinicalcode.tests.constants.constants import API_LINK, CREATE_PHENOTYPE_TEMPLATE_PATH, \
    TEST_CREATE_PHENOTYPE_PATH, PHENOTYPE_ATTR_KEYS, TEMPLATE_JSON_V2_PATH


@pytest.mark.django_db
@pytest.mark.usefixtures("setup_webdriver")
class TestTemplateVersioning:

    @pytest.fixture
    def new_template_definition(self):
        with open(TEMPLATE_JSON_V2_PATH) as f:
            new_template = json.load(f)
        return new_template

    @pytest.fixture
    def template_v2(self, template, new_template_definition):
        template.save()
        template.definition = new_template_definition
        template.template_version = 2
        return template

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_api_data_updated(self, generate_user, user_type, template_v2, live_server):
        user = generate_user[user_type]

        template_v2.created_by = user
        template_v2.save()

        api_request = requests.get(live_server.url + API_LINK)
        api_data = api_request.json()

        assert template_v2.template_version == api_data["version_id"]

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_template_api(self, generate_user, user_type, live_server, template_v2, login):
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
    def test_edit_v1(self, generate_entity, user_type, generate_user, login):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")
        generate_entity.owner = user
        generate_entity.created_by =user
        time.sleep(110)
        # generate_entity.save()
        time.sleep(110)

# pytest -v -s clinicalcode/tests/functional_tests/test_template_versions.py
