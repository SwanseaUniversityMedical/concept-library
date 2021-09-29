from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.permissions import *
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.models.Component import Component
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.Code import Code
from clinicalcode.models.CodeRegex import CodeRegex
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from urlparse import urlparse
from clinicalcode.views.Concept import concept_codes_to_csv
from django.test import RequestFactory

# from django.conf import settings
# from cll import settings as settings_cll
# from cll import test_settings as settings
from cll import test_settings as settings_cll
from rest_framework.reverse import reverse

import time


class RegularExpressionsTest(StaticLiveServerTestCase):

    def setUp(self):

        location = os.path.dirname(__file__)
        if settings_cll.REMOTE_TEST:
            self.browser = webdriver.Remote(command_executor=settings_cll.REMOTE_TEST_HOST,
                                            desired_capabilities=settings_cll.chrome_options.to_capabilities())
            self.browser.implicitly_wait(settings_cll.IMPLICTLY_WAIT)
        else:
            if settings_cll.IS_LINUX:
                self.browser = webdriver.Chrome(os.path.join(location, "chromedriver"),
                                                chrome_options=settings_cll.chrome_options)
            else:
                self.browser = webdriver.Chrome(os.path.join(location, "chromedriver.exe"),
                                                chrome_options=settings_cll.chrome_options)
        super(RegularExpressionsTest, self).setUp()

        self.factory = RequestFactory()

        self.WEBAPP_HOST = self.live_server_url.replace('localhost', '127.0.0.1')
        if settings_cll.REMOTE_TEST:
            self.WEBAPP_HOST = settings_cll.WEBAPP_HOST

        '''data'''
        super_user = User.objects.create_superuser(username=su_user, password=su_password, email=None)
        normal_user = User.objects.create_user(username=nm_user, password=nm_password, email=None)
        self.owner_user = User.objects.create_user(username=ow_user, password=ow_password, email=None)
        group_user = User.objects.create_user(username=gp_user, password=gp_password, email=None)

        permitted_group = Group.objects.create(name="permitted_group")
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

        coding_system2 = CodingSystem.objects.create(
            name="Lookup table 2",
            description="Lookup Codes for testing purposes2",
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
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.EDIT
        )

        self.code_list = self.create_component_with_codes(self, comp_name="included component",
                                                          comp_parent=self.concept_everybody_can_edit,
                                                          code_list_description="included code list",
                                                          codes_names_list=["i1", "i2", "i3"])
        
        update_friendly_id()
        save_stat(self.WEBAPP_HOST)

    def tearDown(self):
        self.browser.quit()
        super(RegularExpressionsTest, self).tearDown()

    def login(self, username, password):
        self.logout()
        self.browser.find_element_by_name('username').send_keys(username)
        self.browser.find_element_by_name('password').send_keys(password)
        self.browser.find_element_by_name('password').send_keys(Keys.ENTER)

    def logout(self):
        self.browser.get('%s%s' % (self.WEBAPP_HOST, '/account/logout/?next=/account/login/'))

    def wait_to_be_logged_in(self, username):
        wait = WebDriverWait(self.browser, 10)
        element = wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'p.navbar-text'), username))

        # Returns logical type of component and list of codes

    # Concept ref for reference to the child concept (optional)
    @staticmethod
    def create_component_with_codes(self, comp_name, comp_parent, code_list_description, codes_names_list):
        component = Component.objects.create(
            component_type=2,
            concept=comp_parent,
            created_by=self.owner_user,
            logical_type=1,
            name=comp_name)

        code_list = CodeList.objects.create(component=component, description=code_list_description)
        code_list.save()
        list_of_codes = []

        codeRegex = CodeRegex.objects.create(component=component, regex_type=1, regex_code="%i%", code_list=code_list)

        for name in codes_names_list:
            code = Code.objects.create(code_list=code_list, code=name, description=name)
            code.save()
            list_of_codes.append(code.code)

        return list_of_codes

    def get_codes_from_response(self, response):
        response = response.splitlines()
        response.pop(0)  # remove headers

        codes = []

        for r in response:
            code = r.split(",")[0]
            codes.append(code)

        print("REPONSE_CODES: ", codes)

        return codes

    '''
        The match with expression functionality makes a copy of the codes, 
        and the code list does not change if the lookup table changes.
    '''

    def test_regular_expression(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                       self.concept_everybody_can_edit.id, '/update/'))

        browser.get(self.WEBAPP_HOST + reverse('concept_update'
                                               , kwargs={'pk': self.concept_everybody_can_edit.id,
                                                         })
                    )

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        coding_system_select = browser.find_element_by_id("id_coding_system")

        # Change lookup table
        coding_system_select.click()
        coding_system_select.send_keys(Keys.DOWN)
        coding_system_select.send_keys(Keys.ENTER)

        browser.find_element_by_id("save-changes").click()  # save changes

#         url = ('%s%s%s' % ('/concepts/C',
#                            self.concept_everybody_can_edit.id, '/export/codes'))
        
        url = self.WEBAPP_HOST + reverse('concept_codes_to_csv'
                                               , kwargs={'pk': self.concept_everybody_can_edit.id}) 
        request = self.factory.get(url)
        request.user = self.owner_user
        request.CURRENT_BRAND = ''

        # make export to csv request
        response = concept_codes_to_csv(request, self.concept_everybody_can_edit.id)

        codes = self.get_codes_from_response(response.content)

        # Assert that the defined codes in setUp appears in the response
        for code in self.code_list:
            self.assertTrue(code in codes, code + " not in response")
