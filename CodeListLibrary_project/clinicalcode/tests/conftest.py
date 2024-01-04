from datetime import datetime
import socket
import time

import pytest
from clinicalcode.models import GenericEntity
from django.contrib.auth.models import User, Group
from django.utils.timezone import make_aware

from selenium.webdriver import Keys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from cll.test_settings import  REMOTE_TEST_HOST, REMOTE_TEST, chrome_options


@pytest.fixture
def generate_user():
    su_user = User.objects.create_superuser(username='superuser', password='superuserpassword', email=None)
    nm_user = User.objects.create_user(username='normaluser', password='normaluserpassword', email=None)
    ow_user = User.objects.create_user(username='owneruser', password='owneruserpassword', email=None)
    gp_user = User.objects.create_user(username='groupuser', password='groupuserpassword', email=None)
    vgp_user = User.objects.create_user(username='viewgroupuser', password='viewgroupuserpassword', email=None)
    egp_user = User.objects.create_user(username='editgroupuser', password='editgroupuserpassword', email=None)

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


@pytest.fixture(scope="class")
def setup_webdriver(request):

    driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=chrome_options)
    wait = WebDriverWait(driver, 10)
    driver.maximize_window()
    request.cls.driver = driver
    request.cls.wait = wait
    yield
    driver.quit()


def pytest_configure(config):
    config.option.liveserver = socket.gethostbyname(socket.gethostname())

@pytest.fixture(scope="function")
def login(live_server):
    def _login(driver, username, password):
        driver.get(live_server.url + "/account/login/")
        print(driver.page_source)
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        # Input username and password
        username_input.send_keys(username)
        password_input.send_keys(password)

        # Submit the form by pressing Enter
        password_input.send_keys(Keys.ENTER)

    yield _login


@pytest.fixture(scope="function")
def logout(live_server):
    def _logout(driver):
        driver.get(live_server.url + "/account/logout/")
    yield _logout



@pytest.fixture(autouse=True)
def use_debug(settings):
    settings.DEBUG = True
    