import random
import time
from datetime import datetime

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from rest_framework.reverse import reverse

from clinicalcode.models.Brand import Brand
from clinicalcode.models.Concept import *
from clinicalcode.models.Phenotype import *
from clinicalcode.models.Tag import Tag
from clinicalcode.models.WorkingSet import *
from clinicalcode.tests.test_base import *
# from django.conf import settings
# from cll import settings as settings_cll
# from cll import test_settings as settings
from cll import test_settings as settings_cll
import string


class SearchTest(StaticLiveServerTestCase):

    def setUp(self):
        location = os.path.dirname(__file__)
        self.NUM_PHENOTYPES = 70
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

        self.permitted_group = Group.objects.create(name="permitted_group")
        # Add the group to the group-user's groups.
        group_user.groups.add(self.permitted_group)

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
            tags=[1],

            is_deleted=False,
            owner=self.owner_user,
            group=self.permitted_group,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )
        self.brand = self.create_brand("HDRUK", "cll/static/img/brands/HDRUK")

        self.nameTags = ["Phenotype_library", "ADP", "BREATHE", "CALIBER", "PIONEER", "SAIL", "BHF DSC"]
        self.collectionOftags = []

        for i in range(len(self.nameTags)):
            self.collectionOftags.append(self.creat_tag(self.nameTags[i], self.brand))

        self.test_phenotypes = []
        for i in range(self.NUM_PHENOTYPES):
            self.test_phenotypes.append(
                self.create_test_phenotype("Phenotype" + str(i + 1), "desc" + str(i + 1),
                                           tags=[random.randrange(len(self.nameTags)) + 1],
                                           group=self.permitted_group, is_deleted=random.choice([True, False])))

        update_friendly_id()

    def create_test_phenotype(self, name, description, tags, group, is_deleted):
        phenotype = Phenotype.objects.create(
            name=str(name),
            description="phenotype level " + str(description),
            author="the_test_goat_author" + str(name),
            layout="Phenotype",
            valid_event_data_range="01/01/1999 - 01/07/2016",
            phenotype_uuid="ideeee" + str(name),
            is_deleted=is_deleted,

            type=random.choice(["Disease or Syndrome", "Biomarker", "Lifestyle Risk Factor"]),
            sex="Female,Male",
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
            owner=self.owner_user,
            group_access=Permissions.EDIT,
            tags=tags,
            group=group,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        ).save()
        return phenotype

    def creat_tag(self, nametag, brand):
        tag = Tag.objects.create(
            collection_brand=brand,
            description=nametag,
            created_by=self.owner_user,
            tag_type=2,
            display=random.randint(1, 6)
        ).save()
        return tag

    def create_brand(self, nameBrand, pathBrand):
        brand = Brand.objects.create(
            name=nameBrand,
            description='',
            logo_path=pathBrand,
            css_path=pathBrand,
            owner=self.owner_user
        ).save()

        return brand

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

    def test_tags_filter(self):
        self.login(su_user, su_password)
        browser = self.browser

        # Go to phenotype list
        browser.get(self.WEBAPP_HOST + reverse('phenotype_list')
                    )

        checkboxes = browser.find_elements_by_name("collection_id")

        # Iterate through checkboxes and make sure they are available
        for i in range(len(checkboxes)):
            browser.find_elements_by_name("collection_id")[i].click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_elements_by_name("collection_id")[i].click()

            updated_element = browser.find_elements_by_name("collection_id")[i]

            self.assertTrue(updated_element.is_enabled())

        time.sleep(settings_cll.TEST_SLEEP_TIME)

    def test_tags_onrelevance(self):

        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('phenotype_list')
                    )

        checkboxes = browser.find_elements_by_name("collection_id")

        # Iterate through checkboxes and compare phenotype tags with actual chosen tag
        for i in range(1, len(checkboxes)):

            browser.find_elements_by_name("collection_id")[i].click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            element = browser.find_elements_by_class_name("col-sm-12")

            tag = browser.find_elements_by_class_name("form-check-label")[i - 1].text

            for j in range(1, len(element), 2):
                self.assertEqual(element[j].text, tag)

            browser.find_elements_by_name("collection_id")[i].click()

    def test_unexpected_symbol_search(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('phenotype_list')
                    )
        browser.find_element_by_xpath("//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements_by_name("collection_id")

        # Iterate through ceckboxes and test could search bar handle the random symbols
        for i in range(1, len(checkboxes)):
            browser.find_elements_by_name("collection_id")[i].click()

            browser.find_element_by_id("search").send_keys("Phenotype")

            browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

            self.assertTrue("No phenotypes" not in browser.page_source)

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_element_by_id("reset-form").click()

            # generate random symbol
            randomstring = ''.join(
                [random.choice(string.ascii_letters + string.digits + string.punctuation) for i in range(5)])

            browser.find_element_by_id("search").send_keys(randomstring)

            browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

            self.assertTrue("No phenotypes" in browser.page_source)

            browser.find_element_by_id("reset-form").click()

    def test_unexpected_phenotype_name(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('phenotype_list')
                    )
        browser.find_element_by_xpath("//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements_by_name("collection_id")

        # Iterate through checkboxes and test if search bar could find the unexpected name of the phenotype
        for i in range(1, len(checkboxes)):
            browser.find_elements_by_name("collection_id")[i].click()

            browser.find_element_by_id("search").send_keys("Phenotype")

            browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            self.assertTrue("No phenotypes" not in browser.page_source)

            browser.find_element_by_id("reset-form").click()

            randomstring = ''.join(
                [random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(5)])

            # Create test phenotype
            self.create_test_phenotype(randomstring, "desc", [i], self.permitted_group, False)

            browser.find_element_by_id("search").send_keys(randomstring)

            browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

            self.assertTrue("No phenotypes" not in browser.page_source)

            browser.find_element_by_id("reset-form").click()

    def test_blank_search_input(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('phenotype_list')
                    )
        browser.find_element_by_xpath("//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements_by_name("collection_id")

        # Test how search bar could handle the empty search
        for i in range(1, len(checkboxes)):
            browser.find_elements_by_name("collection_id")[i].click()

            browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_element_by_id("search").send_keys(Keys.SPACE)

            browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            # Todo Should be discussed
            self.assertTrue("No phenotypes" not in browser.page_source)

            browser.find_element_by_id("reset-form").click()

            browser.find_elements_by_name("collection_id")[i].click()

    def test_blank_phenotype_search(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('phenotype_list')
                    )
        browser.find_element_by_xpath("//*[@id='show-advanced-search']").click()

        # Test if blank phenotype could be exist

        browser.find_element_by_id("search").send_keys(Keys.SPACE)

        browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        self.assertTrue("No phenotypes" in browser.page_source)

        # Reset and create phenotype
        browser.find_element_by_id("reset-form").click()

        self.create_test_phenotype(" ", "desc", [1], self.permitted_group, False)

        browser.find_element_by_id("search").send_keys(Keys.SPACE)

        browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

        self.assertTrue("No phenotypes" not in browser.page_source)

    def test_all_tag(self):

        # Test 'all' tag when user wants to delete the previous search
        self.login(su_user, su_password)

        browser = self.browser
        self.create_test_phenotype("test", "desc", [1], self.permitted_group, False)

        browser.get(self.WEBAPP_HOST + reverse('phenotype_list'))

        browser.find_element_by_xpath("//*[@id='show-advanced-search']").click()

        browser.find_elements_by_name("collection_id")[0].click()

        browser.find_element_by_id("search").send_keys("test")

        browser.find_element_by_xpath('//button[@class = "btn btn-primary"]').click()

        self.assertTrue("No phenotypes" not in browser.page_source)

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element_by_id("search").clear()

        browser.find_elements_by_name("collection_id")[0].click()

       # self.assertTrue(browser.find_element_by_id("search").text is None)

        time.sleep(1000)
