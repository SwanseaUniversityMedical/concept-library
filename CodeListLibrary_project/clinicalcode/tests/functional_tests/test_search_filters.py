from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.permissions import *
from clinicalcode.models.Phenotype import *
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.models.Component import Component
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.CodeRegex import CodeRegex
from clinicalcode.models.Code import Code
from clinicalcode.models.Tag import Tag
from clinicalcode.models.Brand import Brand
from clinicalcode.models.ConceptTagMap import ConceptTagMap
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from rest_framework.reverse import reverse
from urlparse import urlparse
import unittest

# from django.conf import settings
# from cll import settings as settings_cll
# from cll import test_settings as settings
from cll import test_settings as settings_cll

import time


class SearchTest(StaticLiveServerTestCase):

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
        super(SearchTest, self).setUp()

        self.WEBAPP_HOST = self.live_server_url.replace('localhost', '127.0.0.1')
        if settings_cll.REMOTE_TEST:
            self.WEBAPP_HOST = settings_cll.WEBAPP_HOST
        # self.factory = RequestFactory()

        # Users: a normal user and a super_user.
        self.normal_user = User.objects.create_user(username=nm_user, password=nm_password, email=None)
        super_user = User.objects.create_superuser(username=su_user, password=su_password, email=None)
        self.owner_user = User.objects.create_user(username=ow_user, password=ow_password, email=None)
        group_user = User.objects.create_user(username=gp_user, password=gp_password, email=None)

        permitted_group = Group.objects.create(name="permitted_group")
        # Add the group to the group-user's groups.
        group_user.groups.add(permitted_group)
        brand =

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
            tags=[18],

            is_deleted=False,
            owner=self.owner_user,
            group=permitted_group,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )

        self.test_phenotypes = []
        for i in range(10):
            self.test_phenotypes.append(self.create_test_phenotype(i+1, "desc" + str(i+1), tags=[18],group=permitted_group))

        self.tag = Tag.objects.create(
                description="tagTest",
                created_by=self.owner_user,

            )
        self.tag.save()

        '''self.conceptTag = ConceptTagMap.objects.create(
            concept=self.concept1,
            tag = self.tag,
            created_by=self.owner_user
        )'''



        update_friendly_id()

    def create_test_phenotype(self, name, description, tags, group):
        phenotype = Phenotype.objects.create(
            name="Phenotype" + str(name),
            description="phenotype level " + str(description),
            author="the_test_goat",
            layout="Phenotype",
            valid_event_data_range="01/01/1999 - 01/07/2016",
            phenotype_uuid="ideeee"+str(name),

            type="Biomarker",
            sex = "Female,Male",
            phenoflowid=4,
            concept_informations='[{"concept_version_id": %s, "concept_id": %s, "attributes": []}]' % (
                str(self.concept_everybody_can_edit.id), str(self.concept_everybody_can_edit.id)),
            validation_performed=False,
            publication_doi="",
            publication_link=Google_website,
            source_reference=Google_website,

            validation="",
            publications=[],
            status="FINAL",
            secondary_publication_links="",
            citation_requirements="",
            created_by=self.owner_user,
            updated_by=self.owner_user,
            is_deleted=False,
            owner=self.owner_user,
            group_access=Permissions.EDIT,
            tags=tags,
            group=group,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        ).save()
        return phenotype



    def tearDown(self):
        self.browser.quit()
        super(SearchTest, self).tearDown()

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

    def test_history_tags(self):
        self.login(su_user, su_password)

        browser = self.browser
        time.sleep(1000)
