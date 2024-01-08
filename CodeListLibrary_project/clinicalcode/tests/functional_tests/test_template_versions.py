import json
import os
import shutil

import pytest
import requests
import yaml
from pyconceptlibraryclient import Client
from selenium.webdriver.common.by import By

from clinicalcode.tests.constants.constants import TEST_TEMPLATE_PATH, API_URL, CREATE_PHENOTYPE_TEMPLATE_PATH, \
    TEST_CREATE_PHENOTYPE_PATH, PHENOTYPE_ATTR_KEYS


# with open(TEST_TEMPLATE_PATH) as f:
#     data = json.load(f)
#
# print(data)
#
# # REMOTE_TEST_HOST = 'http://selenium-hub-1:4444/wd/hub'
#
# chrome_options = webdriver.ChromeOptions()
# chrome_options.add_experimental_option("prefs", {'profile.managed_default_content_settings.javascript': 'enable'})
# chrome_options.accept_insecure_certs = True
# chrome_options.accept_ssl_certs = True
#
# # Add your options as needed
# options = [
#     "--window-size=1200,1200",
#     "--ignore-certificate-errors",
#     "--ignore-ssl-errors",
#     "--window-size=1280,800",
#     "--verbose",
#     "--start-maximized",
#     "--disable-gpu",
#     "--allow-insecure-localhost",
#     "--disable-dev-shm-usage",
#     "--allow-running-insecure-content"
#     # '--headless' #if need debug localy through selenim container comment this line
# ]
# WEBAPP_HOST = "http://localhost:8000/"
# for option in options:
#     chrome_options.add_argument(option)
# driver = webdriver.Chrome(options=chrome_options)
#
# driver.get(WEBAPP_HOST + "/account/login/")
# username_input = driver.find_element(By.NAME, "username")
# password_input = driver.find_element(By.NAME, "password")
#
# username_input.send_keys("tobyr")
# password_input.send_keys("tobyr")
# password_input.send_keys(Keys.ENTER)
#
# driver.get(WEBAPP_HOST + "admin/clinicalcode/template/1/change/")
# template_input = driver.find_element(By.NAME, "definition")
# template_input.clear()
# template_input.send_keys(json.dumps(data))
# save_button = driver.find_element(By.NAME, "_save")
# save_button.click()
#
# # Test to check if api is updates with the new template
# x = requests.get(WEBAPP_HOST + "api/v1/templates/1/version/2/detail")

# Test number 2

@pytest.mark.django_db
@pytest.mark.usefixtures("setup_webdriver", "get_template")
class TestTemplateVersioning:

    @pytest.fixture
    def get_template(self):
        with open(TEST_TEMPLATE_PATH) as f:
            new_template = json.load(f)
        return new_template

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_api_data_updated(self, get_template, login, generate_user, user_type, live_server):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")
        self.driver.get(live_server + "admin/clinicalcode/template/1/change/")
        template_input = self.driver.find_element(By.NAME, "definition")
        template_input.clear()
        template_input.send_keys(json.dumps(get_template))
        save_button = self.driver.find_element(By.NAME, "_save")
        save_button.click()
        print("New template added")

        api_request = requests.get(API_URL + "templates/1/detail/")
        api_data = api_request.json()

        assert get_template["template_details"]['version'] == api_data["version_id"]

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_template_api(self, generate_user, user_type, live_server):
        user = generate_user[user_type]
        client = Client(
            username=user.username, password= user.username + "password",
            url=live_server.url
        )
        shutil.copy(CREATE_PHENOTYPE_TEMPLATE_PATH, TEST_CREATE_PHENOTYPE_PATH)

        client.phenotypes.create(TEST_CREATE_PHENOTYPE_PATH)

        with open(CREATE_PHENOTYPE_TEMPLATE_PATH) as stream:
            read_yaml = yaml.load(stream, Loader=yaml.FullLoader)

        with open(TEST_CREATE_PHENOTYPE_PATH) as stream:
            create_yaml = yaml.load(stream, Loader=yaml.FullLoader)

        for key in PHENOTYPE_ATTR_KEYS:
            create_yaml.pop(key)
        # os.remove(TEST_CREATE_PHENOTYPE_PATH)

        assert create_yaml == read_yaml






# clinicalcode/tests/functional_tests/test_template_versions.py