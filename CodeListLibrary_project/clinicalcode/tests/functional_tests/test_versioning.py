import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse

from clinicalcode.db_utils import getGroupOfCodesByConceptId_HISTORICAL
from clinicalcode.models.Code import Code
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.Component import Component
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.permissions import *
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.views.Concept import concept_codes_to_csv
from clinicalcode.views.WorkingSet import workingset_to_csv
# from django.conf import settings
# from cll import settings as settings_cll
# from cll import test_settings as settings
from cll import test_settings as settings_cll
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import RequestFactory
from rest_framework.reverse import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class VersioningTest(StaticLiveServerTestCase):

    def setUp(self):
        location = os.path.dirname(__file__)
        if settings_cll.REMOTE_TEST:
            self.browser = webdriver.Remote(
                command_executor=settings_cll.REMOTE_TEST_HOST,
                desired_capabilities=settings_cll.chrome_options.
                to_capabilities())
            self.browser.implicitly_wait(settings_cll.IMPLICTLY_WAIT)
        else:
            if settings_cll.IS_LINUX:
                self.browser = webdriver.Chrome(
                    os.path.join(location, "chromedriver"),
                    chrome_options=settings_cll.chrome_options)
            else:
                self.browser = webdriver.Chrome(
                    os.path.join(location, "chromedriver.exe"),
                    chrome_options=settings_cll.chrome_options)
        super(VersioningTest, self).setUp()

        super(VersioningTest, self).setUp()

        self.factory = RequestFactory()

        self.WEBAPP_HOST = self.live_server_url.replace('localhost', '127.0.0.1')
        if settings_cll.REMOTE_TEST:
            self.WEBAPP_HOST = settings_cll.WEBAPP_HOST
        '''data'''
        super_user = User.objects.create_superuser(username=su_user, password=su_password, email=None)
        self.normal_user = User.objects.create_user(username=nm_user, password=nm_password, email=None)
        owner_user = User.objects.create_user(username=ow_user, password=ow_password, email=None)
        group_user = User.objects.create_user(username=gp_user, password=gp_password, email=None)

        # Groups: a group that is not permitted and one that is.
        permitted_group = Group.objects.create(name="permitted_group")
        # Add the group to the group-user's groups.
        group_user.groups.add(permitted_group)

        coding_system = CodingSystem.objects.create(
            name="Lookup table",
            description="Lookup Codes for testing purposes",
            link=Google_website,
            database_connection_name="default",
            table_name="clinicalcode_lookup",
            code_column_name="code",
            desc_column_name="description")
        coding_system.save()

        self.concept_everybody_can_edit = Concept.objects.create(
            name="concept everybody can edit",
            description="concept description",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=super_user,
            modified_by=super_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.EDIT)

        self.child_concept = Concept.objects.create(
            name="child concept",
            description="child concept",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=super_user,
            modified_by=super_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.VIEW)

        self.component = Component.objects.create(
            comment="child concept",
            component_type=1,
            concept=self.concept_everybody_can_edit,
            concept_ref=self.child_concept,
            created_by=owner_user,
            logical_type=1,
            name="child concept")

        self.component = Component.objects.create(
            comment="Component visibility test",
            component_type=2,
            concept=self.concept_everybody_can_edit,
            created_by=owner_user,
            logical_type=1,
            name="Component")

        self.code_list = CodeList.objects.create(
            component=self.component, description="Code list visibility test")
        self.code = Code.objects.create(code_list=self.code_list,
                                        code="45554",
                                        description="visibility test")

        # concept is updated two times to make hisotry
        self.concept_everybody_can_edit.author = "the_test_goat2"
        self.concept_everybody_can_edit.save()
        self.concept_everybody_can_edit.author = "the_test_goat2"
        self.concept_everybody_can_edit.save()

        concept_info_list = [{str(self.concept_everybody_can_edit.id):{"ttt|4":"yyy"}}] 

        self.workingset_everybody_can_edit = WorkingSet.objects.create(
            name="wokringset everybody can access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            concept_informations=concept_info_list,
            concept_version={
                (str(self.concept_everybody_can_edit.id)):
                str(self.concept_everybody_can_edit.history.first().history_id)
            },
            group=permitted_group,
            group_access=Permissions.VIEW,
            owner_access=Permissions.VIEW,
            world_access=Permissions.EDIT)

        # workingset is updated two times to make hisotry
        self.workingset_everybody_can_edit.author = "the_test_goat2"
        self.workingset_everybody_can_edit.save()
        self.workingset_everybody_can_edit.author = "the_test_goat2"
        self.workingset_everybody_can_edit.save()

        update_friendly_id()
        save_stat(self.WEBAPP_HOST)

    def tearDown(self):
        self.browser.quit()
        super(VersioningTest, self).tearDown()

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

    def get_codes_from_response(self, response):
        response = response.splitlines()
        response.pop(0)  # remove headers

        codes = []

        for r in response:
            code = r.split(",")[0]
            codes.append(code)

        codes.sort()
        # self.output.sort()
        print(("REPONSE_CODES: ", codes))

        return codes

    '''
    Every version of a code list has a version ID (formerly the history ID)
    '''

    def test_concept_every_version_has_id(self):
        self.login(nm_user, nm_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept_everybody_can_edit.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        table = self.browser.find_element(By.ID, 'history-table')
        table_rows = table.find_elements_by_tag_name('tr')

        i = 1
        for row in table_rows:
            test = True
            if i != 1:  # omit first row which contains headers
                table_data = row.find_elements_by_tag_name('td')
                id = table_data[0].text
                if id is None:
                    test = False
                else:
                    try:
                        id = int(table_data[0].text)
                    except:
                        test = False

                self.assertTrue(test)
            i += 1

    def test_workingset_every_version_has_id(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        print(("WORKINGSET ID", self.workingset_everybody_can_edit.id))
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                          self.workingset_everybody_can_edit.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('workingset_detail',
                            kwargs={
                                'pk': self.workingset_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        # self.wait_to_be_logged_in(ow_user)

        table = self.browser.find_element(By.ID, 'history-table')
        table_rows = table.find_elements_by_tag_name('tr')

        i = 1
        for row in table_rows:
            test = True
            if i != 1:  # omit first row which contains headers
                table_data = row.find_elements_by_tag_name('td')
                id = table_data[0].text
                if id is None:
                    test = False
                else:
                    try:
                        id = int(table_data[0].text)
                    except:
                        test = False

                self.assertTrue(test)
            i += 1

    '''
    The version ID is displayed along with the title.
    '''

    def test_concept_every_version_has_title(self):
        self.login(nm_user, nm_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept_everybody_can_edit.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        table = self.browser.find_element(By.ID, 'history-table')
        table_rows = table.find_elements_by_tag_name('tr')

        i = 1
        for row in table_rows:
            test = True
            if i != 1:  # omit first row which contains headers
                table_data = row.find_elements_by_tag_name('td')
                title = table_data[1].text
                self.assertEqual(title, self.concept_everybody_can_edit.name)
            i += 1

    def test_workingset_every_version_has_title(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        print(("WORKINGSET ID", self.workingset_everybody_can_edit.id))
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                         self.workingset_everybody_can_edit.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('workingset_detail',
                            kwargs={
                                'pk': self.workingset_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        table = self.browser.find_element(By.ID, 'history-table')
        table_rows = table.find_elements_by_tag_name('tr')

        i = 1
        for row in table_rows:
            test = True
            if i != 1:  # omit first row which contains headers
                table_data = row.find_elements_by_tag_name('td')
                title = table_data[1].text
                self.assertEqual(title,
                                 self.workingset_everybody_can_edit.name)
            i += 1

    '''
    There is a URL to refer to a specific version of a code list
    '''

    def test_concept_every_version_has_url(self):
        self.login(nm_user, nm_password)

        browser = self.browser
        # get the test server url
        #  browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                           self.concept_everybody_can_edit.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        links = self.browser.find_elements(By.CLASS_NAME, 'version-link')

        id_index = 0
        for link in links:
            url = link.get_attribute("href")
            u = urlparse(url)
            # check if url is valid
            self.assertEqual(u.scheme, 'http')
            path = u.path.split('/')
            # check if url contains concept id
            self.assertEqual(int(path[2]), self.concept_everybody_can_edit.id)
            # check if url contains unique history id
            version_id = self.concept_everybody_can_edit.history.all(
            )[id_index].history_id
            self.assertEqual(int(path[4]), version_id)
            id_index += 1

    def test_workingset_every_version_has_url(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s' % (self.WEBAPP_HOST, '/workingsets/'))

        browser.get(self.WEBAPP_HOST + reverse('workingset_list'))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        links = self.browser.find_elements(By.CLASS_NAME, 'version-link')

        id_index = 0
        for link in links:
            url = link.get_attribute("href")
            u = urlparse(url)
            # check if url is valid
            self.assertEqual(u.scheme, 'http')
            path = u.path.split('/')
            # check if url contains workingset id
            self.assertEqual(int(path[2]),
                             self.workingset_everybody_can_edit.id)
            # check if url contains unique history id
            version_id = self.workingset_everybody_can_edit.history.all(
            )[id_index].history_id
            self.assertEqual(int(path[4]), version_id)
            id_index += 1

    '''
        There is a URL that always refers to the latest version of a code list
    '''

    def test_concept_has_url_to_latest_ver(self):

        latest_version = self.concept_everybody_can_edit.history.first(
        ).history_id

        self.login(nm_user, nm_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                              self.concept_everybody_can_edit.id, '/version/',
        #                             latest_version, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_history_detail',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                                'concept_history_id': latest_version
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        #         url = ('%s%s%s' % ('/concepts/C',
        #                            self.concept_everybody_can_edit.id, '/export/codes'))

        url = self.WEBAPP_HOST + reverse(
            'concept_codes_to_csv',
            kwargs={'pk': self.concept_everybody_can_edit.id})
        request = self.factory.get(url)
        request.user = self.normal_user
        request.CURRENT_BRAND = ''

        # make export to csv request
        response = concept_codes_to_csv(request,
                                        self.concept_everybody_can_edit.id)

        codes = self.get_codes_from_response(response.content.decode('utf-8'))

        historical_codes = getGroupOfCodesByConceptId_HISTORICAL(
            self.concept_everybody_can_edit.id, latest_version)[0]['code']

        # test if live codes equals historical codes
        self.assertEqual(codes[0], historical_codes)

        title = self.browser.find_element(By.TAG_NAME, 'h2').text
        # title = self.browser.find_elements_by_tag_name('i')

        # test if page contains concept name
        self.assertTrue(self.concept_everybody_can_edit.name in title)

    def test_workingset_has_url_to_latest_ver(self):
        latest_version = self.workingset_everybody_can_edit.history.first(
        ).history_id

        self.login(nm_user, nm_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                              self.workingset_everybody_can_edit.id, '/version/',
        #                             latest_version, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('workingset_history_detail',
                            kwargs={
                                'pk': self.workingset_everybody_can_edit.id,
                                'workingset_history_id': latest_version
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        #         url = ('%s%s%s' % ('/workingsets/WS',
        #                            self.workingset_everybody_can_edit.id, '/export/codes'))

        url = self.WEBAPP_HOST + reverse(
            'workingset_to_csv',
            kwargs={'pk': self.workingset_everybody_can_edit.id})
        request = self.factory.get(url)
        request.user = self.normal_user
        request.CURRENT_BRAND = ''

        # make export to csv request
        response = workingset_to_csv(request,
                                     self.workingset_everybody_can_edit.id)

        codes = self.get_codes_from_response(response.content.decode('utf-8'))

        # check if workingset returns code contained by concept
        self.assertEqual(codes, ['45554'])

        title = self.browser.find_element(By.TAG_NAME, 'h2').text

        # title = self.browser.find_elements_by_tag_name('i')

        # test if page contains concept name
        self.assertTrue(self.workingset_everybody_can_edit.name in title)

    '''
        The API can get the latest version of a code list
    '''

    def test_concept_has_url_to_latest_ver_in_api(self):
        latest_version = self.concept_everybody_can_edit.history.first().history_id

        self.login(nm_user, nm_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST)

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # get the test server url
        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_concept_codes/',
        #                       self.concept_everybody_can_edit.id))

        browser.get(self.WEBAPP_HOST +
                    reverse('api:api_export_concept_codes',
                            kwargs={'pk': self.concept_everybody_can_edit.id}))

        tree = ET.fromstring(browser.page_source)

        for x in tree.iter("concept_version_id"):
            self.assertEqual(int(x.text), latest_version)

    def test_workingset_has_url_to_latest_ver_in_api(self):
        latest_version = self.concept_everybody_can_edit.history.first().history_id

        self.login(nm_user, nm_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST)

        browser.get(self.WEBAPP_HOST + reverse('api:api_export_workingset_codes', kwargs={'pk': self.workingset_everybody_can_edit.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        tree = ET.fromstring(browser.page_source)

        for x in tree.iter("concept_version_id"):
            self.assertEqual(int(x.text), latest_version)

    '''
    The API can get a specific version of a code list
    '''

    def test_concept_api_get_specific_version(self):

        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get(self.WEBAPP_HOST)


        browser.get(self.WEBAPP_HOST +
                    reverse('api:api_export_concept_codes',
                            kwargs={'pk': self.concept_everybody_can_edit.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue(
            self.code.code in browser.page_source
            and self.concept_everybody_can_edit.name in browser.page_source)

    def test_workingset_api_get_specific_version(self):

        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get(self.WEBAPP_HOST)

        browser.get(self.WEBAPP_HOST + reverse(
            'api:api_export_workingset_codes_byVersionID',
            kwargs={
                'pk':
                self.workingset_everybody_can_edit.id,
                'workingset_history_id':
                self.workingset_everybody_can_edit.history.first().history_id
            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue(
            self.code.code in browser.page_source
            and self.concept_everybody_can_edit.name in browser.page_source)

    '''
    When a child concept is added to a parent concept, it adds the latest version by default (but the version number can be changed).
    '''

    def test_latest_version_exist_after_adding_child(self):
        # get latest version
        latest_version = self.concept_everybody_can_edit.history.first(
        ).history_id

        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept_everybody_can_edit.id, '/update/'))
        browser.get(self.WEBAPP_HOST +
                    reverse('concept_update',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        # add child
        # try to add child
        browser.find_element(By.ID, 'conceptTypes').click()

        browser.implicitly_wait(5)
        browser.find_element(By.ID, 'addConcept').click()

        wait = WebDriverWait(self.browser, 10)
        wait.until(
            EC.presence_of_element_located((By.ID, "concept-search-text")))

        concept_search_field = browser.find_element(By.ID,
                                                    "concept-search-text")

        time.sleep(3)  # wait to load component form

        concept_search_field.send_keys("concept")

        time.sleep(3)  # wait to load concept prompt

        concept_search_field.send_keys(Keys.DOWN)
        concept_search_field.send_keys(Keys.ENTER)

        browser.find_element(By.ID, "saveBtn").click()

        time.sleep(4)  # wait to submition be completed

        latest_version_after_adding_child = self.concept_everybody_can_edit.history.first(
        ).history_id
        self.assertNotEqual(latest_version, latest_version_after_adding_child)

    '''
    When a child concept is updated, the parent concept does not change
    '''

    def test_concept_version_when_child_concept_updated(self):
        latest_version = self.concept_everybody_can_edit.history.first(
        ).history_id

        self.child_concept.author = "the_test_goat2"
        self.child_concept.save()

        latest_version_after_child_updatge = self.concept_everybody_can_edit.history.first(
        ).history_id

        self.assertEqual(latest_version, latest_version_after_child_updatge)
