from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.permissions import *
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.models.Component import Component
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.CodeRegex import CodeRegex
from clinicalcode.models.Code import Code
from clinicalcode.models.Tag import Tag
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from rest_framework.reverse import reverse
from urllib.parse import urlparse
import unittest

# from django.conf import settings
# from cll import settings as settings_cll
# from cll import test_settings as settings
from cll import test_settings as settings_cll

import time


class HistoryTest(StaticLiveServerTestCase):

    def setUp(self):

        location = os.path.dirname(__file__)
        if settings_cll.REMOTE_TEST:
            self.browser = webdriver.Remote(command_executor=settings_cll.REMOTE_TEST_HOST,
                                            desired_capabilities=settings_cll.chrome_options.to_capabilities())
            self.browser.implicitly_wait(settings_cll.IMPLICTLY_WAIT)
        else:
            if settings_cll.IS_LINUX:
                self.browser = webdriver.Chrome(os.path.join(
                    location, "chromedriver"), chrome_options=settings_cll.chrome_options)
            else:
                self.browser = webdriver.Chrome(os.path.join(
                    location, "chromedriver.exe"), chrome_options=settings_cll.chrome_options)
        super(HistoryTest, self).setUp()

        self.WEBAPP_HOST = self.live_server_url.replace('localhost', '127.0.0.1')
        if settings_cll.REMOTE_TEST:
            self.WEBAPP_HOST = settings_cll.WEBAPP_HOST
        # self.factory = RequestFactory()

        self.owner_user = User.objects.create_user(
            username=ow_user, password=ow_password, email=None)

        coding_system = CodingSystem.objects.create(
            name="Lookup table",
            description="Lookup Codes for testing purposes",
            link=Google_website,
            database_connection_name="test_code_list_library",
            table_name="clinicalcode_code",
            code_column_name="CODE",
            desc_column_name="DESCRIPTION")
        coding_system.save()
        
        
        self.tag = Tag.objects.create(
            description="tagTest",
            created_by=self.owner_user
        )
        self.tag.save()        

        self.concept1 = Concept.objects.create(
            name="concept level 4",
            description="concept level 4",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=self.owner_user,
            modified_by=self.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=self.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT,
            tags = '{'+str(self.tag.id)+'}'
        )




        self.comp1 = self.create_component_with_codes(self, comp_type=4, log_type=1, comp_name="comp1",
                                                      comp_parent=self.concept1,
                                                      code_list_description="com1 comp 1",
                                                      codes_names_list=["i1", "i2"])

        self.comp_pk = self.comp1[0].pk

        self.codes = self.comp1[2]
        
        update_friendly_id()
        save_stat(self.WEBAPP_HOST)

    def tearDown(self):
        self.browser.quit()
        super(HistoryTest, self).tearDown()

    def login(self, username, password):
        self.logout()
        self.browser.find_element(By.NAME,'username').send_keys(username)
        self.browser.find_element(By.NAME,'password').send_keys(password)
        self.browser.find_element(By.NAME,'password').send_keys(Keys.ENTER)

    def logout(self):
        self.browser.get('%s%s' % (self.WEBAPP_HOST, '/account/logout/?next=/account/login/'))

    def wait_to_be_logged_in(self, username):
        wait = WebDriverWait(self.browser, 10)
        element = wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'p.navbar-text'), username))

        # Returns logical type of component and list of codes

    # Concept ref for reference to the child concept (optional)
    @staticmethod
    def create_component_with_codes(self, comp_type, log_type, comp_name, comp_parent, code_list_description,
                                    codes_names_list, concept_ref=None, concept_ref_history_id=None):
        component = Component.objects.create(
            component_type=comp_type,
            concept=comp_parent,
            created_by=self.owner_user,
            logical_type=log_type,
            name=comp_name)

        # if component type is child concept add reference to the child
        if comp_type == 1:
            component.concept_ref = concept_ref
            component.concept_ref_history_id = concept_ref_history_id

        code_list = CodeList.objects.create(
            component=component, description=code_list_description)
        list_of_codes = []

        codeRegex = CodeRegex.objects.create(
            component=component, regex_type=1, regex_code="i%", code_list=code_list, column_search=1)

        codeRegex.save()

        for name in codes_names_list:
            code = Code.objects.create(
                code_list=code_list, code=name, description="isudhfsuidhf")
            code.save()
            list_of_codes.append(code)

        code_list.save()
        component.save()
        comp_parent.save()

        return component, log_type, list_of_codes

    '''
        Select/express component is edited then concept is saved.
        The test checks if latest historical version of the concept contains
        the correct version of the component.
    '''

    def test_select_comp_after_edit(self):

        # remove one code and update the concept
        code = Code.objects.filter(id=self.codes[0].id)
        code.delete()
        self.concept1.save()

        self.login(ow_user, ow_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept1.id, '/update/'))
        browser.get(self.WEBAPP_HOST + reverse('concept_update'
                                               , kwargs={'pk': self.concept1.id,
                                                         })
                    )

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # go to the latest historical version of the concept
        href = "/concepts/C" + str(self.concept1.id) + "/version/" + str(
            self.concept1.history.first().history_id) + "/detail/"
        browser.find_element(By.XPATH,'//a[@href="' + href + '"]').click()

        # click the component details button
        id = "code-preview-" + str(self.comp_pk)
        browser.find_element(By.XPATH,'//button[@id="' + id + '"]').click()

        time.sleep(2)

        rows = browser.find_elements(By.XPATH,'//tbody[@id="expressionSelectContentArea"]/tr')
        # make sure there is one row of codes (there is one code)
        self.assertEqual(len(rows), 1)

        # check the name of the code
        name = browser.find_element(By.XPATH,'//tbody[@id="expressionSelectContentArea"]/tr/td').text
        self.assertEqual(name, "i2")

    '''
        Concept with a tag is created. Test checks if the latest historical version
        of the concept contains the tag.
    '''

    def test_history_tags(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        # get the test server url
        browser.get('%s%s' % (self.WEBAPP_HOST, '/concepts/create'))

        browser.get(self.WEBAPP_HOST + reverse('concept_create'
                                               , kwargs=None)
                    )

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # create a concept
        browser.find_element(By.ID,'id_name').send_keys("concept2")
        tagField = browser.find_element_by_class_name('tt-input')
        tagField.send_keys("tag")

        time.sleep(2)  # wait to load concept prompt

        # click on a prompt to fill the field
        tagField.send_keys(Keys.DOWN)
        tagField.send_keys(Keys.ENTER)

        browser.find_element(By.ID,'id_author').send_keys("conceptAuthor")
        browser.find_element(By.ID,'id_description').send_keys("concept2222222")
        browser.find_element(By.ID,'id_coding_system').send_keys(Keys.DOWN)

        browser.find_element(By.ID,'save-changes').click()

        concept = Concept.objects.all().order_by('-id')[0]

        # go to the latest historical version of the concept
        href = "/concepts/C" + str(concept.id) + "/version/" + str(concept.history.first().history_id) + "/detail/"
        browser.find_element(By.XPATH,'//a[@href="' + href + '"]').click()

        # TO-DO assertTrue or equal that tag exist
        self.assertTrue("tagTest" in browser.page_source)
