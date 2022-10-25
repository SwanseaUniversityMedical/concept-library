import sys
import time
from datetime import datetime
from os.path import dirname
from unittest import skip, skipIf

from clinicalcode.models.WorkingSet import *
from clinicalcode.permissions import *
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
# from django.conf import settings
# from cll import read_only_test_settings
# from cll import test_settings as settings
from cll import read_only_test_settings as settings
from decouple import Config, RepositoryEnv
from django.contrib.auth import logout
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

''' 
    If arguments does not contain read_only substring then skip the test
    because it means that read only settings are not used and tests will fail.
    See manage.py to see how it works.
'''


@skipIf('read_only' not in sys.argv[-1], "READ ONLY TEST SKIPPED")
class ReadOnlyTestWorkingSet(StaticLiveServerTestCase):

    def setUp(self):

        location = dirname(dirname(__file__))
        if settings.REMOTE_TEST:
            self.browser = webdriver.Remote(
                command_executor=settings.REMOTE_TEST_HOST,
                desired_capabilities=settings.chrome_options.to_capabilities())
        else:
            if settings.IS_LINUX:
                self.browser = webdriver.Chrome(
                    os.path.join(location, "chromedriver"),
                    chrome_options=settings.chrome_options)
            else:
                self.browser = webdriver.Chrome(
                    os.path.join(location, "chromedriver.exe"),
                    chrome_options=settings.chrome_options)
        super(ReadOnlyTestWorkingSet, self).setUp()

        self.WEBAPP_HOST = self.live_server_url.replace(
            'localhost', '127.0.0.1')
        if settings.REMOTE_TEST:
            self.WEBAPP_HOST = settings.WEBAPP_HOST

        # Users: a normal user and a super_user.
        super_user = User.objects.create_superuser(username=su_user,
                                                   password=su_password,
                                                   email=None)
        normal_user = User.objects.create_user(username=nm_user,
                                               password=nm_password,
                                               email=None)
        owner_user = User.objects.create_user(username=ow_user,
                                              password=ow_password,
                                              email=None)
        group_user = User.objects.create_user(username=gp_user,
                                              password=gp_password,
                                              email=None)
        view_group_user = User.objects.create_user(username=vgp_user,
                                                   password=vgp_password,
                                                   email=None)
        edit_group_user = User.objects.create_user(username=egp_user,
                                                   password=egp_password,
                                                   email=None)

        # Groups: a group that is not permitted and one that is.
        permitted_group = Group.objects.create(name="permitted_group")
        forbidden_group = Group.objects.create(name="forbidden_group")
        view_group = Group.objects.create(name="view_group")
        edit_group = Group.objects.create(name="edit_group")
        # Add the group to the group-user's groups.
        group_user.groups.add(permitted_group)
        view_group_user.groups.add(view_group)
        edit_group_user.groups.add(edit_group)

        self.workingset_everybody_can_edit = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.EDIT,
            owner_access=Permissions.NONE,
            world_access=Permissions.EDIT)

        update_friendly_id()
        save_stat(self.WEBAPP_HOST)

    def tearDown(self):
        self.browser.quit()
        super(ReadOnlyTestWorkingSet, self).tearDown()

    def login(self, username, password):
        self.logout()
        self.browser.find_element(By.NAME, 'username').send_keys(username)
        self.browser.find_element(By.NAME, 'password').send_keys(password)
        self.browser.find_element(By.NAME, 'password').send_keys(Keys.ENTER)

    def logout(self):
        self.browser.get(
            '%s%s' %
            (self.WEBAPP_HOST, '/account/logout/?next=/account/login/'))

    def wait_to_be_logged_in(self, username):
        wait = WebDriverWait(self.browser, 10)
        element = wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, 'p.navbar-text'), username))

    '''
    A user cannot revert a working set.
    '''

    def test_normal_user_cannot_revert(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get(
            '%s%s%s%s%s%s' %
            (self.WEBAPP_HOST, '/workingsets/WS',
             self.workingset_everybody_can_edit.id, '/version/',
             self.workingset_everybody_can_edit.history.first().history_id,
             '/detail/'))

        time.sleep(settings.TEST_SLEEP_TIME)

        exist = True
        try:
            button = self.browser.find_element(By.ID, 'revert-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)

            return True
        except NoSuchElementException:
            exist = False

        self.assertFalse(exist)

    def test_normal_user_cannot_revert_through_url(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get(
            '%s%s%s%s%s%s' %
            (self.WEBAPP_HOST, '/workingsets/WS',
             self.workingset_everybody_can_edit.id, '/version/',
             self.workingset_everybody_can_edit.history.first().history_id,
             '/revert/'))

        time.sleep(settings.TEST_SLEEP_TIME)
        # self.wait_to_be_logged_in(nm_user)
        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_owner_cannot_revert(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get(
            '%s%s%s%s%s%s' %
            (self.WEBAPP_HOST, '/workingsets/WS',
             self.workingset_everybody_can_edit.id, '/version/',
             self.workingset_everybody_can_edit.history.first().history_id,
             '/detail/'))

        time.sleep(settings.TEST_SLEEP_TIME)

        exist = True
        try:
            button = self.browser.find_element(By.ID, 'revert-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)

            return True
        except NoSuchElementException:
            exist = False

        self.assertFalse(exist)

    def test_owner_cannot_revert_through_url(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get(
            '%s%s%s%s%s%s' %
            (self.WEBAPP_HOST, '/workingsets/WS',
             self.workingset_everybody_can_edit.id, '/version/',
             self.workingset_everybody_can_edit.history.first().history_id,
             '/revert/'))
        time.sleep(settings.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    '''
    A super user CANNOT create, edit, revert a working set.
    '''

    def test_super_user_cannot_create(self):
        browser = self.browser
        # get the test server url
        browser.get('%s%s' % (self.WEBAPP_HOST, '/workingsets/create/'))

        self.login(su_user, su_password)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_super_user_cannot_edit(self):
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' %
                    (self.WEBAPP_HOST, '/workingsets/WS',
                     self.workingset_everybody_can_edit.id, '/update/'))

        self.login(su_user, su_password)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_super_user_cannot_revert(self):
        browser = self.browser
        # get the test server url
        browser.get(
            '%s%s%s%s%s%s' %
            (self.WEBAPP_HOST, '/workingsets/WS',
             self.workingset_everybody_can_edit.id, '/version/',
             self.workingset_everybody_can_edit.history.first().history_id,
             '/detail/'))

        self.login(su_user, su_password)

        exist = True
        try:
            button = self.browser.find_element(By.ID, 'revert-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)

            return True
        except NoSuchElementException:
            exist = False

        self.assertFalse(exist)

    def test_super_user_cannot_revert_through_url(self):
        browser = self.browser
        # get the test server url
        browser.get(
            '%s%s%s%s%s%s' %
            (self.WEBAPP_HOST, '/workingsets/WS',
             self.workingset_everybody_can_edit.id, '/version/',
             self.workingset_everybody_can_edit.history.first().history_id,
             '/revert/'))

        self.login(su_user, su_password)
        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    '''
    A user cannot edit by creating their own URL string to bypass the interface.
    '''

    def test_normal_user_cannot_edit_by_own_url(self):
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' %
                    (self.WEBAPP_HOST, '/workingsets/WS',
                     self.workingset_everybody_can_edit.id, '/update/'))

        self.login(nm_user, nm_password)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_owner_cannot_edit_by_own_url(self):
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' %
                    (self.WEBAPP_HOST, '/workingsets/WS',
                     self.workingset_everybody_can_edit.id, '/update/'))

        self.login(ow_user, ow_password)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)
