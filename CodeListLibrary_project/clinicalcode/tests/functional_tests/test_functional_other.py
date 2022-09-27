import random
import time
from datetime import datetime

from clinicalcode.models import Tag, Brand
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
from cll import test_settings as settings_cll
from decouple import Config, RepositoryEnv
from django.conf import settings as setting_django
from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import (Client, LiveServerTestCase, RequestFactory,
                         override_settings)
from rest_framework.reverse import reverse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# from django.conf import settings
# from cll import settings as settings_cll
# from cll import test_settings as settings


class OtherTest(StaticLiveServerTestCase):

    def setUp(self):
        #       chrome_options = webdriver.ChromeOptions()

        #         chrome_options.add_experimental_option( "prefs",{'profile.managed_default_content_settings.javascript': 'enable'})
        #         chrome_options.add_argument('--headless')
        #         chrome_options.add_argument("--no-sandbox")
        #         chrome_options.add_argument("--disable-dev-shm-usage")
        #
        #         chrome_options.add_argument("--start-maximized")
        #         chrome_options.add_argument("--disable-gpu")
        #         #chrome_options.add_argument("--window-size=1280,800")
        #         chrome_options.add_argument("--allow-insecure-localhost")

        self.factory = RequestFactory()

        location = os.path.dirname(__file__)
        if settings_cll.REMOTE_TEST:
            self.browser = webdriver.Remote(
                command_executor=settings_cll.REMOTE_TEST_HOST,
                desired_capabilities=settings_cll.chrome_options.
                to_capabilities())
        else:
            if settings_cll.IS_LINUX:
                self.browser = webdriver.Chrome(
                    os.path.join(location, "chromedriver"),
                    chrome_options=settings_cll.chrome_options)
            else:
                self.browser = webdriver.Chrome(
                    os.path.join(location, "chromedriver.exe"),
                    chrome_options=settings_cll.chrome_options)
        super(OtherTest, self).setUp()

        self.WEBAPP_HOST = self.live_server_url.replace(
            'localhost', '127.0.0.1')
        if settings_cll.REMOTE_TEST:
            self.WEBAPP_HOST = self.WEBAPP_HOST

        # Users: a normal user and a super_user.
        self.normal_user = User.objects.create_user(username=nm_user,
                                                    password=nm_password,
                                                    email=None)
        super_user = User.objects.create_superuser(username=su_user,
                                                   password=su_password,
                                                   email=None)
        self.owner_user = User.objects.create_user(username=ow_user,
                                                   password=ow_password,
                                                   email=None)
        group_user = User.objects.create_user(username=gp_user,
                                              password=gp_password,
                                              email=None)

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

        self.brand = self.create_brand("HDRUK", "cll/static/img/brands/HDRUK")

        self.nameTags = [
            "Phenotype_library", "ADP", "BREATHE", "CALIBER", "PIONEER",
            "SAIL", "BHF DSC"
        ]
        self.collectionOftags = []

        for i in range(len(self.nameTags)):
            self.collectionOftags.append(
                self.creat_tag(self.nameTags[i], self.brand))

        self.concept_everybody_can_view = Concept.objects.create(
            name="concept everybody can view",
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
            tags=[1],
            code_attribute_header=[],
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.VIEW)
        self.concept_everybody_can_view.save()

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
            tags=[1],
            created_by=super_user,
            modified_by=super_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.EDIT)

        self.concept_none_can_access = Concept.objects.create(
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
            tags=[1],
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.EDIT,
            owner_access=Permissions.NONE,
            world_access=Permissions.NONE)

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
            owner=self.owner_user,
            tags=[1],
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.VIEW)

        self.concept_with_excluded_codes = Concept.objects.create(
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
            tags=[1],
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.EDIT)

        component = Component.objects.create(
            comment="child concept",
            component_type=1,
            concept=self.concept_everybody_can_view,
            concept_ref=self.child_concept,
            concept_ref_history_id=self.child_concept.history.first(
            ).history_id,
            created_by=self.owner_user,
            logical_type=1,
            name="child concept")

        code_child = CodeList.objects.create(component=component,
                                             description="child")
        self.code_child = Code.objects.create(code_list=code_child,
                                              code="45512354",
                                              description="child test")

        component_excluded = Component.objects.create(
            comment="Component 2 exclusion",
            component_type=2,
            concept=self.concept_with_excluded_codes,
            created_by=self.owner_user,
            logical_type=2,
            name="Component 2 exclusion")

        code_list = CodeList.objects.create(component=component_excluded,
                                            description="Code list exclusion")
        self.code_excluded1 = Code.objects.create(code_list=code_list,
                                                  code="45554",
                                                  description="Exclusion Test")
        self.code_excluded2 = Code.objects.create(code_list=code_list,
                                                  code="24212",
                                                  description="Exclusion test")

        self.concept_with_excluded_and_included_codes = Concept.objects.create(
            name="child concept",
            description="child concept",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            tags=[1],
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
            world_access=Permissions.VIEW)

        component_included = Component.objects.create(
            comment="Component 2 exclusion",
            component_type=2,
            concept=self.concept_with_excluded_and_included_codes,
            created_by=self.owner_user,
            logical_type=1,
            name="Component 2 exclusion")

        component_excluded2 = Component.objects.create(
            comment="Component 2 exclusion",
            component_type=2,
            concept=self.concept_with_excluded_and_included_codes,
            created_by=self.owner_user,
            logical_type=2,
            name="Component 2 exclusion")

        code_list_excluded = CodeList.objects.create(
            component=component_excluded2, description="Code list exclusion")
        code_list_included = CodeList.objects.create(
            component=component_included, description="Code list inclusion")

        # These are the same two instances of the same code to make it included and excluded
        self.code_excluded3 = Code.objects.create(
            code_list=code_list_excluded,
            code="1111",
            description="Inclusion/Exclusion test")
        self.code_included = Code.objects.create(
            code_list=code_list_included,
            code="1111",
            description="Inclusion/Exclusion Test")

        self.workingset_everybody_can_view = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"3":{"ttt|3":"yyy"}}],
            concept_version={"3": 1},
            created_by=super_user,
            updated_by=super_user,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.VIEW,
            owner_access=Permissions.VIEW,
            world_access=Permissions.VIEW)

        self.workingset_everybody_can_edit = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{str(self.concept_everybody_can_view.id):{"ttt|3":"yyy"}}, 
                                  {str(self.concept_everybody_can_edit.id):{"ttt|3":"yyy"}}],
            concept_version={
                (str(self.concept_everybody_can_view.id)):
                self.concept_everybody_can_view.history.first().history_id,
                (str(self.concept_everybody_can_edit.id)):
                self.concept_everybody_can_edit.history.first().history_id
            },
            created_by=super_user,
            updated_by=super_user,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.VIEW,
            owner_access=Permissions.VIEW,
            world_access=Permissions.EDIT)

        self.workingset_none_can_access = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{str(self.concept_everybody_can_view.id):{"ttt|3":"yyy"}}],
            concept_version={
                (str(self.concept_everybody_can_view.id)):
                self.concept_everybody_can_view.history.first().history_id
            },
            created_by=super_user,
            updated_by=super_user,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.EDIT,
            world_access=Permissions.NONE)

        concept_info_list = [{str(self.concept_with_excluded_codes.id):{"ttt|3":"yyy"}}] 

        self.workingset_with_excluded_codes = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=concept_info_list,
            concept_version={
                (str(self.concept_with_excluded_codes.id)):
                self.concept_with_excluded_codes.history.first().history_id
            },
            # "1"
            created_by=super_user,
            updated_by=super_user,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.EDIT,
            world_access=Permissions.NONE)

        concept_info_list2 = [{str(self.concept_with_excluded_and_included_codes.id):{"ttt|3":"yyy"}}] 

        self.workingset_with_excluded_and_included_codes = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=concept_info_list2,
            concept_version={
                (str(self.concept_with_excluded_and_included_codes.id)):
                self.concept_with_excluded_and_included_codes.history.first().
                history_id
            },
            # "1"
            created_by=super_user,
            updated_by=super_user,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.EDIT,
            world_access=Permissions.NONE)

        update_friendly_id()
        save_stat(self.WEBAPP_HOST)

    def creat_tag(self, nametag, brand):
        tag = Tag.objects.create(collection_brand=brand,
                                 description=nametag,
                                 created_by=self.owner_user,
                                 tag_type=2,
                                 display=random.randint(1, 6)).save()
        return tag

    def create_brand(self, nameBrand, pathBrand):
        brand = Brand.objects.create(name=nameBrand,
                                     description='',
                                     logo_path=pathBrand,
                                     css_path=pathBrand,
                                     owner=self.owner_user).save()
        return brand

    def tearDown(self):
        # self.browser.refresh()
        self.browser.quit()
        super(OtherTest, self).tearDown()

    def login(self, username, password):
        self.logout()
        self.browser.find_element(By.NAME, 'username').send_keys(username)
        self.browser.find_element(By.NAME, 'password').send_keys(password)
        self.browser.find_element(By.NAME, 'password').send_keys(Keys.ENTER)

    def logout(self):
        # self.browser.get('%s%s' % (self.WEBAPP_HOST, '/account/logout/?next=/account/login/'))
        self.browser.get(
            '%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'),
                      '/account/logout/?next=/account/login/'))

    def wait_to_be_logged_in(self, username):
        wait = WebDriverWait(self.browser, 10)
        element = wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, 'p.navbar-text'), username))

    '''
    If one or more of workingset concepts is deleted or revoked permission 
    I do not have permission to view, cannot export csv and run api
    '''

    def test_revoking_permission(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                           self.concept_everybody_can_edit.id, '/update/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_update',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        browser.find_element(
            By.XPATH,
            ".//input[@type='radio' and @name='world_access' and @value='1']"
        ).click()  # Change world access permission to none
        browser.find_element(By.ID, "save-changes").click()  # save

        self.logout()
        # ----------------------
        self.login(nm_user, nm_password)  # logging as normal user
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                         self.workingset_everybody_can_edit.id, '/detail/'))

        browser.get(
            self.WEBAPP_HOST +
            reverse('workingset_detail',
                    kwargs={'pk': self.workingset_everybody_can_edit.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        export_button = self.browser.find_element(By.ID, 'export-btn')
        is_disabled = export_button.get_attribute("disabled")
        self.assertTrue(is_disabled)

        # Try to export to csv bu URL
        # Todo needs to be confirmed which url should be used for reverse
        browser.get('%s%s%s%s' %
                    (self.WEBAPP_HOST, '/workingsets/WS',
                     self.concept_everybody_can_view.id, '/export/concepts/'))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_workingset_codes/',
        #                        self.workingset_everybody_can_edit.id))

        browser.get(
            self.WEBAPP_HOST +
            reverse('api:api_export_workingset_codes',
                    kwargs={'pk': self.workingset_everybody_can_edit.id}))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("You do not have permission to perform this action."
                        or "Permission denied" in browser.page_source)

    def test_deleting_concept(self):
        self.login(ow_user, ow_password)

        browser = self.browser
        # get the test server url
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                         self.concept_everybody_can_edit.id, '/delete/'))
        browser.get(self.WEBAPP_HOST +
                    reverse('concept_delete',
                            kwargs={
                                'pk': self.concept_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        submit_button = browser.find_element(
            By.XPATH, "//button[@type='submit']").click()

        is_deleted = Concept.objects.get(
            pk=self.concept_everybody_can_edit.id).is_deleted
        # print(self.concept_everybody_can_edit.id)
        self.assertTrue(
            is_deleted,
            "concept is not deleted!")  # make sure that concept is deleted

        self.logout()
        # --------------------
        self.login(nm_user, nm_password)  # logging as normal user

        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                          self.workingset_everybody_can_edit.id, '/detail/'))
        #
        browser.get(self.WEBAPP_HOST +
                    reverse('workingset_detail',
                            kwargs={
                                'pk': self.workingset_everybody_can_edit.id,
                            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        export_button = self.browser.find_element(By.ID, 'export-btn')
        # print(str(export_button))
        is_disabled = export_button.get_attribute("disabled")
        # print(is_disabled)
        self.assertTrue(is_disabled)

        # Try to export to csv bu URL
        # Todo needs to be confirmed which url should be used for reverse
        browser.get('%s%s%s%s' %
                    (self.WEBAPP_HOST, '/workingsets/WS',
                     self.concept_everybody_can_view.id, '/export/concepts/'))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_workingset_codes/',
        #                        self.workingset_everybody_can_edit.id))

        browser.get(
            self.WEBAPP_HOST +
            reverse('api:api_export_workingset_codes',
                    kwargs={'pk': self.workingset_everybody_can_edit.id}))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("You do not have permission to perform this action."
                        or "Permission denied" in browser.page_source)

    '''
    Check if user has access to update, delete, API when 
    concept world access value is set to VIEW. test export button AND API
    '''

    def test_access_to_concept_update(self):

        self.login(nm_user, nm_password)

        browser = self.browser
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                         self.concept_everybody_can_view.id, '/update/'))
        browser.get(self.WEBAPP_HOST +
                    reverse('concept_update',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_access_to_concept_delete(self):
        deleted_concept = self.concept_everybody_can_view
        deleted_concept.is_deleted = True
        deleted_concept.save()

        self.login(nm_user, nm_password)

        browser = self.browser
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          deleted_concept.id, '/delete/'))

        browser.get(
            self.WEBAPP_HOST +
            reverse('concept_delete', kwargs={'pk': deleted_concept.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        # print("bps="+browser.page_source)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

        # self.logout()

    def test_access_to_concept_revert(self):

        self.login(nm_user, nm_password)

        browser = self.browser
        # browser.get('%s%s%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                             self.concept_everybody_can_view.id, '/version/',
        #                            self.concept_everybody_can_view.history.first().history_id, '/revert/'))
        browser.get(self.WEBAPP_HOST + reverse(
            'concept_history_revert',
            kwargs={
                'pk':
                self.concept_everybody_can_view.id,
                'concept_history_id':
                self.concept_everybody_can_view.history.first().history_id
            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        # self.login(nm_user, nm_password)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_access_to_workingset_update(self):

        self.login(nm_user, nm_password)

        browser = self.browser
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                          self.concept_everybody_can_view.id, '/update/'))
        browser.get(self.WEBAPP_HOST +
                    reverse('workingset_update',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_access_to_workingset_delete(self):

        self.login(nm_user, nm_password)
        browser = self.browser
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                          self.concept_everybody_can_view.id, '/delete/'))
        browser.get(self.WEBAPP_HOST +
                    reverse('workingset_delete',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_access_to_workingset_revert(self):

        self.login(nm_user, nm_password)

        browser = self.browser
        # browser.get('%s%s%s%s%s%s' % (self.WEBAPP_HOST, '/workingsets/WS',
        #                              self.concept_everybody_can_view.id, '/version/',
        #                             self.concept_everybody_can_view.history.first().history_id, '/revert/'))

        browser.get(self.WEBAPP_HOST + reverse(
            'workingset_history_revert',
            kwargs={
                'pk':
                self.concept_everybody_can_view.id,
                'workingset_history_id':
                self.concept_everybody_can_view.history.first().history_id
            }))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        # print(browser.page_source )
        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source)

    def test_concept_api(self):
        self.login(nm_user, nm_password)

        browser = self.browser

        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_concept_codes/',
        #                        self.concept_none_can_access.id))

        browser.get(self.WEBAPP_HOST +
                    reverse('api:api_export_concept_codes',
                            kwargs={'pk': self.concept_none_can_access.id}))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("You do not have permission to perform this action."
                        or "Permission denied" in browser.page_source)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/concepts/C',
        #                       self.concept_none_can_access.id))

        browser.get(self.WEBAPP_HOST +
                    reverse('api:concept_by_id',
                            kwargs={
                                'pk': self.concept_none_can_access.id,
                            }))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("Not found." in browser.page_source)

    def test_workingset_api(self):
        self.login(nm_user, nm_password)

        browser = self.browser
        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_workingset_codes/',
        #                        self.workingset_none_can_access.id))

        browser.get(self.WEBAPP_HOST +
                    reverse('api:api_export_workingset_codes',
                            kwargs={'pk': self.workingset_none_can_access.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("You do not have permission to perform this action."
                        or "Permission denied" in browser.page_source)

    '''
    If one or more child concepts of a concept is deleted or 
    revoked permission I do not have permission to view
    '''

    def test_child_concept_revoked_permission(self):
        self.login(nm_user, nm_password)

        browser = self.browser

        # check if normal user can see concept
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                         self.concept_everybody_can_view.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # user should be able to see concept
        self.assertTrue("403: Permission denied" not in browser.page_source
                        and  # or
                        "500: Page unavailable" not in browser.page_source)

        self.logout()

        # login as owner and change permission
        self.login(ow_user, ow_password)

        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                         self.child_concept.id, '/update/'))

        browser.get(
            self.WEBAPP_HOST +
            reverse('concept_update', kwargs={
                'pk': self.child_concept.id,
            }))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        browser.find_element(
            By.XPATH,
            ".//input[@type='radio' and @name='world_access' and @value='1']"
        ).click()  # Change world access permission to none
        browser.find_element(By.ID, "save-changes").click()  # save

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_update',
                            kwargs={
                                'pk': self.concept_everybody_can_view.id,
                            }))
        # Update the child concept
        browser.find_element(By.XPATH, '//*[@title="Edit component"]').click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        # Time wait for changes for cicking apply button
        browser.find_element(By.ID, "saveBtn2").click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        self.logout()

        # login again as normal user and check if permission denied appears for concept with child
        self.login(nm_user, nm_password)
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept_everybody_can_view.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        export_button = self.browser.find_element(By.ID, 'export-btn')
        is_disabled = export_button.get_attribute("disabled")

        self.assertTrue(is_disabled)

        # Try to export csv bu using URL
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept_everybody_can_view.id, '/export/codes/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_codes_to_csv',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source
                        or "Not found." in browser.page_source)

    def test_child_concept_deleted(self):
        self.login(nm_user, nm_password)

        browser = self.browser

        # check if normal user can see concept
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.concept_everybody_can_view.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # user should be able to see concept
        self.assertTrue("403: Permission denied" not in browser.page_source
                        or "500: Page unavailable" not in browser.page_source)

        self.logout()

        # login as owner and delete concept
        self.login(ow_user, ow_password)

        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                          self.child_concept.id, '/delete/'))
        browser.get(
            self.WEBAPP_HOST +
            reverse('concept_delete', kwargs={'pk': self.child_concept.id}))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        submit_button = browser.find_element(
            By.XPATH, "//button[@type='submit']").click()

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_update',
                            kwargs={
                                'pk': self.concept_everybody_can_view.id,
                            }))

        # Time wait for changes for cicking apply button to save current parent concept
        browser.find_element(By.ID, "save-changes").click()  # save

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        self.logout()

        # login again as normal user and check if permission denied appears for concept with child
        self.login(nm_user, nm_password)
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                         self.concept_everybody_can_view.id, '/detail/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_detail',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)
        export_button = self.browser.find_element(By.ID, 'export-btn')

        is_disabled = export_button.get_attribute("disabled")
        self.assertTrue(is_disabled)

        # Try to export csv bu using URL
        # browser.get('%s%s%s%s' % (self.WEBAPP_HOST, '/concepts/C',
        #                         self.concept_everybody_can_view.id, '/export/codes/'))

        browser.get(self.WEBAPP_HOST +
                    reverse('concept_codes_to_csv',
                            kwargs={'pk': self.concept_everybody_can_view.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        self.assertTrue("403: Permission denied" in browser.page_source
                        or "500: Page unavailable" in browser.page_source
                        or "Not found." in browser.page_source)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_concept_codes/',
        #                       self.workingset_everybody_can_edit.id))

        # self.assertTrue("Permission denied" in browser.page_source)

    '''
    BrowsableAPI
    '''

    def test_if_buttons_exist(self):
        self.login(nm_user, nm_password)

        browser = self.browser
        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        #browser.get('%s%s' % (self.WEBAPP_HOST, '/api/'))
        browser.get('%s%s' %
                    (self.WEBAPP_HOST, reverse('api:root', kwargs={})))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        exist = True
        try:
            browser.find_element(By.XPATH, '//button[text()="OPTIONS"]')
            browser.find_element(By.XPATH, '//a[text()="GET"]')
        except NoSuchElementException:
            exist = False

        self.assertFalse(exist)

    def test_api_is_not_browsable(self):

        # self.assertTrue('rest_framework.renderers.BrowsableAPIRenderer' not in settings.REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'])
        test = True
        if setting_django.BROWSABLEAPI == True:
            test = False

        if 'DEFAULT_RENDERER_CLASSES' in setting_django.REST_FRAMEWORK:
            if 'rest_framework.renderers.BrowsableAPIRenderer' in setting_django.REST_FRAMEWORK[
                    'DEFAULT_RENDERER_CLASSES']:
                test = False
                print((
                    "FROM ELSE: ",
                    setting_django.REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']))
        else:
            test = False  # browsable=fail

        self.assertTrue(test)

    '''
    Test inclusion and exclusion of codes in a concept. (export CSV and API)
    '''

    def test_concept_codes_exclusion(self):
        #         url = ('%s%s%s' % ('/concepts/C',
        #                            self.concept_with_excluded_codes.id, '/export/codes'))

        url = self.WEBAPP_HOST + reverse(
            'concept_codes_to_csv',
            kwargs={'pk': self.concept_with_excluded_codes.id})

        request = self.factory.get(url)
        request.user = self.normal_user
        request.CURRENT_BRAND = ''

        # pass request to the view
        response = concept_codes_to_csv(request,
                                        self.concept_with_excluded_codes.id)

        print(("RESPONSE ", response.content.decode('utf-8')))

        codes = response.content.decode(
            'utf-8')  # list with response content which contains codes
        test_code1 = self.code_excluded1.code
        test_code2 = self.code_excluded2.code  #

        test = True
        if test_code1 in codes or test_code2 in codes:
            test = False

        self.assertTrue(test)

    def test_concept_codes_exclusion_in_api(self):
        self.login(nm_user, nm_password)

        browser = self.browser

        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_concept_codes/',
        #                       self.concept_with_excluded_codes.id))

        browser.get(
            self.WEBAPP_HOST +
            reverse('api:api_export_concept_codes',
                    kwargs={'pk': self.concept_with_excluded_codes.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        test_code1 = self.code_excluded1.code
        test_code2 = self.code_excluded2.code

        # Make sure that codes do not appear in API
        self.assertFalse(test_code1 in browser.page_source
                         or test_code2 in browser.page_source)

    def test_concept_codes_inclusion_and_exclusion(self):
        #         url = ('%s%s%s' % ('/concepts/C',
        #                            self.concept_with_excluded_and_included_codes.id, '/export/codes'))

        url = self.WEBAPP_HOST + reverse(
            'concept_codes_to_csv',
            kwargs={'pk': self.concept_with_excluded_and_included_codes.id})

        request = self.factory.get(url)
        request.user = self.normal_user
        request.CURRENT_BRAND = ''

        # pass request to the view
        response = concept_codes_to_csv(
            request, self.concept_with_excluded_and_included_codes.id)

        codes = response.content.decode(
            'utf-8')  # list with response content which contains codes
        test_code1 = self.code_included.code
        test_code2 = self.code_excluded3.code

        test = True
        if test_code1 in codes or test_code2 in codes:
            test = False

        self.assertTrue(test)

    def test_concept_codes_exclusion_and_inclusion_in_api(self):
        self.login(nm_user, nm_password)

        browser = self.browser

        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_concept_codes/',
        #                       self.concept_with_excluded_codes.id))

        browser.get(
            self.WEBAPP_HOST +
            reverse('api:api_export_concept_codes',
                    kwargs={'pk': self.concept_with_excluded_codes.id}))

        time.sleep(settings_cll.TEST_SLEEP_TIME)

        test_code1 = self.code_included.code
        test_code2 = self.code_excluded3.code

        # Make sure that codes do not appear in API
        self.assertFalse(test_code1 in browser.page_source
                         or test_code2 in browser.page_source)

    def test_workingset_exclusion_and_inclusion(self):
        #         url = ('%s%s%s' % ('/workingsets/WS',
        #                            self.workingset_with_excluded_codes.id, '/export/concepts'))

        url = self.WEBAPP_HOST + reverse(
            'workingset_to_csv',
            kwargs={'pk': self.workingset_with_excluded_codes.id})
        request = self.factory.get(url)
        request.user = self.owner_user
        request.CURRENT_BRAND = ''

        # pass request to the view
        response = workingset_to_csv(request,
                                     self.workingset_with_excluded_codes.id)

        codes = response.content.decode(
            'utf-8')  # list with response content which contains codes
        test_code1 = self.code_excluded1.code
        test_code2 = self.code_excluded2.code

        test = True
        if test_code1 in codes or test_code2 in codes:
            test = False

        self.assertTrue(test)

    def test_workingset_exclusion(self):
        #         url = ('%s%s%s' % ('/workingsets/WS',
        #                            self.workingset_with_excluded_and_included_codes.id, '/export/concepts'))

        url = self.WEBAPP_HOST + reverse(
            'workingset_to_csv',
            kwargs={'pk': self.workingset_with_excluded_and_included_codes.id})
        request = self.factory.get(url)
        request.user = self.owner_user
        request.CURRENT_BRAND = ''

        # pass request to the view
        response = workingset_to_csv(
            request, self.workingset_with_excluded_and_included_codes.id)

        codes = response.content.decode(
            'utf-8')  # list with response content which contains codes
        test_code1 = self.code_included.code
        test_code2 = self.code_excluded3.code

        test = True
        if test_code1 in codes or test_code2 in codes:
            test = False

        self.assertTrue(test)

    def test_export_workingset_codes_exclusion_and_inclusion_in_api(self):
        self.login(ow_user, ow_password)

        browser = self.browser

        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_workingset_codes/',
        #                        self.workingset_with_excluded_and_included_codes.id))

        browser.get(self.WEBAPP_HOST + reverse(
            'api:api_export_workingset_codes',
            kwargs={'pk': self.workingset_with_excluded_and_included_codes.id})
                    )
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        test_code1 = self.code_included.code
        test_code2 = self.code_excluded3.code

        # Make sure that codes do not appear in API
        self.assertFalse(test_code1 in browser.page_source
                         or test_code2 in browser.page_source)

    def test_export_workingset_codes_exclusion_in_api(self):
        self.login(ow_user, ow_password)

        browser = self.browser

        browser.get('%s' % (self.WEBAPP_HOST))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        # browser.get('%s%s%s' % (self.WEBAPP_HOST, '/api/export_workingset_codes/',
        #                       self.workingset_with_excluded_codes.id))

        browser.get(
            self.WEBAPP_HOST +
            reverse('api:api_export_workingset_codes',
                    kwargs={'pk': self.workingset_with_excluded_codes.id}))
        time.sleep(settings_cll.TEST_SLEEP_TIME)

        test_code1 = self.code_excluded1.code
        test_code2 = self.code_excluded2.code

        # Make sure that codes do not appear in API
        self.assertFalse(test_code1 in browser.page_source
                         or test_code2 in browser.page_source)

    '''
    Export to CSV permission test
    '''

    def test_concept_to_csv_permission(self):
        #         url = ('%s%s%s' % ('/concepts/C',
        #                            self.concept_none_can_access.id, '/export/codes'))

        url = self.WEBAPP_HOST + reverse(
            'concept_codes_to_csv',
            kwargs={'pk': self.concept_none_can_access.id})

        request = self.factory.get(url)
        request.user = self.normal_user
        request.CURRENT_BRAND = ''

        test = False
        try:
            response = concept_codes_to_csv(request,
                                            self.concept_none_can_access.id)
        except PermissionDenied as error:
            test = True

        self.assertTrue(test)

    def test_workingset_to_csv_permission(self):
        #         url = ('%s%s%s' % ('/workingsets/WS',
        #                            self.workingset_none_can_access.id, '/export/codes'))

        url = self.WEBAPP_HOST + reverse(
            'workingset_to_csv',
            kwargs={'pk': self.workingset_none_can_access.id})

        request = self.factory.get(url)
        request.user = self.normal_user
        request.CURRENT_BRAND = ''

        test = False
        try:
            response = workingset_to_csv(request,
                                         self.workingset_none_can_access.id)
        except PermissionDenied as error:
            test = True

        self.assertTrue(test)
