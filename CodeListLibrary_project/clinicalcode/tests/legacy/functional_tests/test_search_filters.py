import random
import string
import time
from datetime import datetime

from clinicalcode.models.Brand import Brand
from clinicalcode.models.Concept import *
from clinicalcode.models.Phenotype import *
from clinicalcode.models.Tag import Tag
from clinicalcode.models.WorkingSet import *
from clinicalcode.tests.test_base import *
# from cll import test_settings as settings
from cll import test_settings as settings_cll
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
# from django.conf import settings
# from cll import settings as settings_cll
from django.test import RequestFactory
from rest_framework.reverse import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from unittest import skip, skipIf

@skipIf(True, "SEARCH PAGE TEST SKIPPED")
class SearchTest(StaticLiveServerTestCase):
    reset_sequences = True

    def setUp(self):
        location = os.path.dirname(__file__)
        self.NUM_PHENOTYPES = 100

        self.factory = RequestFactory()
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

        super(SearchTest, self).setUp()

        self.WEBAPP_HOST = self.live_server_url.replace(
            'localhost', '127.0.0.1')
        if settings_cll.REMOTE_TEST:
            self.WEBAPP_HOST = settings_cll.WEBAPP_HOST

        self.load_data()

    def load_data(self):
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
            world_access=Permissions.EDIT)
        self.brand = self.create_brand("HDRUK", "cll/static/img/brands/HDRUK")

        self.nameTags = [
            "Phenotype_library", "ADP", "BREATHE", "CALIBER", "PIONEER",
            "SAIL", "BHF DSC"
        ]
        self.collectionOftags = []

        for i in range(len(self.nameTags)):
            self.collectionOftags.append(
                self.creat_tag(self.nameTags[i], self.brand))

        self.test_phenotypes = []
        for i in range(self.NUM_PHENOTYPES):
            self.test_phenotypes.append(
                self.create_test_phenotype(
                    "Phenotype" + str(i + 1),
                    "desc" + str(i + 1),
                    tags=[random.randrange(len(self.nameTags)) + 1],
                    group=self.permitted_group,
                    is_deleted=random.choice([True, False]),
                    owner=self.owner_user,
                    author="test_author"))

        update_friendly_id()
        save_stat(self.WEBAPP_HOST)

    def create_test_phenotype(self, name, description, tags, group, is_deleted,
                              owner, author):
        phenotype = Phenotype.objects.create(
            name=str(name),
            description="phenotype level " + str(description),
            author=author,
            layout="Phenotype",
            valid_event_data_range="01/01/1999 - 01/07/2016",
            phenotype_uuid="ideeee" + str(name),
            is_deleted=is_deleted,
            type=random.choice(
                ["Disease or Syndrome", "Biomarker", "Lifestyle Risk Factor"]),
            sex="Female,Male",
            phenoflowid=4,
            concept_informations= [{"concept_version_id": str(self.concept_everybody_can_edit.id), 
                                    "concept_id": str(self.concept_everybody_can_edit.id), 
                                    "attributes": []}],
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
            owner=owner,
            group_access=Permissions.EDIT,
            tags=tags,
            group=group,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT).save()
        return phenotype

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
        self.browser.quit()
        super(SearchTest, self).tearDown()

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
        wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, 'p.navbar-text'), username))

    def test_tags_filter(self):

        self.login(su_user, su_password)
        browser = self.browser

        # Go to phenotype list
        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        checkboxes = browser.find_elements(By.ID, "collection_id")


        # Iterate through checkboxes and make sure they are available
        for i in range(len(checkboxes)):
            browser.find_elements(By.NAME, "collection_id")[i].click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_elements(By.NAME, "collection_id")[i].click()

            updated_element = browser.find_elements(By.NAME,
                                                    "collection_id")[i]

            self.assertTrue(updated_element.is_enabled())

        time.sleep(settings_cll.TEST_SLEEP_TIME)

    def test_tags_onrelevance(self):

        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        checkboxes = browser.find_elements(By.NAME, "collection_id")

        # Iterate through checkboxes and compare phenotype tags with actual chosen tag
        for i in range(1, len(checkboxes)):

            browser.find_elements(By.NAME, "collection_id")[i].click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            element = browser.find_elements(By.CSS_SELECTOR,
                                            ".col-sm-12 > .tag")

            tag = browser.find_elements(By.CLASS_NAME,
                                        "form-check-label")[i - 1].text

            for j in range(1, len(element), 2):
                self.assertEqual(element[j].text, tag)

            browser.find_elements(By.NAME, "collection_id")[i].click()

    def xx_test_unexpected_symbol_search(self):

        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))
        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements(By.NAME, "collection_id")

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        # Iterate through checkboxes and test could search bar handle the random symbols
        for i in range(1, len(checkboxes)):
            browser.find_elements(By.NAME, "collection_id")[i].click()

            browser.find_element(By.ID, "search").send_keys("Phenotype")

            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()

            self.assertTrue("No phenotypes" not in browser.page_source)

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_element(By.ID, "reset-form").click()

            # generate random symbol
            randomstring = ''.join([
                random.choice(string.ascii_letters + string.digits +
                              string.punctuation) for _ in range(5)
            ])

            browser.find_element(By.ID, "search").send_keys(randomstring)

            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()

            self.assertTrue("No phenotypes" in browser.page_source)

            browser.find_element(By.ID, "reset-form").click()

    def xx_test_unexpected_phenotype_name(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))
        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements(By.NAME, "collection_id")

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        # Iterate through checkboxes and test if search bar could find the unexpected name of the phenotype
        for i in range(1, len(checkboxes)):
            browser.find_elements(By.NAME, "collection_id")[i].click()

            browser.find_element(By.ID, "search").send_keys("Phenotype")

            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            self.assertTrue("No phenotypes" not in browser.page_source)

            browser.find_element(By.ID, "reset-form").click()

            randomstring = ''.join([
                random.choice(string.ascii_letters + string.digits)
                for _ in range(5)
            ])

            # Create test phenotype
            self.create_test_phenotype(randomstring,
                                       "desc", [i],
                                       self.permitted_group,
                                       False,
                                       owner=self.owner_user,
                                       author="author")

            browser.find_element(By.ID, "search").send_keys(randomstring)

            time.sleep(5)

            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()

            time.sleep(10)

            self.assertTrue("No phenotypes" not in browser.page_source)

            browser.find_element(By.ID, "reset-form").click()

    """
    NOT FOR REALEASE 1
    def test_blank_search_input(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes')
                    )
        browser.find_element(By.XPATH,"//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements(By.NAME,"collection_id")

        # Test how search bar could handle the empty search
        for i in range(1, len(checkboxes)):
            browser.find_elements(By.NAME,"collection_id")[i].click()

            browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            # Todo Should be discussed(Test empty in search space)
            browser.find_element(By.ID,"search").send_keys(Keys.SPACE)
            browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()
            time.sleep(settings_cll.IMPLICTLY_WAIT)
            self.assertTrue("No phenotypes" not in browser.page_source)
            browser.find_element(By.ID,"reset-form").click()

            # Test empty in author search space
            browser.find_element(By.NAME,"author").send_keys(Keys.SPACE)
            browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()
            time.sleep(settings_cll.IMPLICTLY_WAIT)
            self.assertTrue("No phenotypes" not in browser.page_source)
            browser.find_element(By.ID,"reset-form").click()

            # Test empty in owner  search space
            browser.find_element(By.NAME,"owner").send_keys(Keys.SPACE)
            browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()
            time.sleep(settings_cll.IMPLICTLY_WAIT)
            self.assertTrue("No phenotypes" not in browser.page_source)
            browser.find_element(By.ID,"reset-form").click()

            browser.find_elements(By.NAME,"collection_id")[i].click()
        """

    def xx_test_blank_phenotype_search(self):
        self.login(su_user, su_password)
        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))
        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        # Test if blank phenotype could be exist

        browser.find_element(By.ID, "search").send_keys(Keys.SPACE)

        browser.find_element(By.XPATH,
                             '//button[@class = "btn btn-primary"]').click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)


        self.assertTrue("No phenotypes" not in browser.page_source)

        # Reset and create phenotype
        browser.find_element(By.ID, "reset-form").click()

        self.create_test_phenotype(" ",
                                   "desc", [1],
                                   self.permitted_group,
                                   False,
                                   owner=self.owner_user,
                                   author="author")

        browser.find_element(By.ID, "search").send_keys(Keys.SPACE)

        browser.find_element(By.XPATH,
                             '//button[@class = "btn btn-primary"]').click()


        self.assertTrue("No phenotypes" not in browser.page_source)

    def xx_test_all_tag(self):

        # Test 'all' tag when user wants to delete the previous search
        self.login(su_user, su_password)

        browser = self.browser
        self.create_test_phenotype("test",
                                   "desc", [1],
                                   self.permitted_group,
                                   False,
                                   owner=self.owner_user,
                                   author="test_author")

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        browser.find_elements(By.NAME, "collection_id")[0].click()

        browser.find_element(By.ID, "search").send_keys("test")

        browser.find_element(By.XPATH,
                             '//button[@class = "btn btn-primary"]').click()

        self.assertTrue("No phenotypes" not in browser.page_source)

        browser.find_element(By.ID, "search").clear()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_elements(By.NAME, "collection_id")[0].click()
        print(browser.find_element(By.ID, "search").text)

        self.assertTrue(browser.find_element(By.ID, "search").text == "")

    def xx_test_search(self):
        self.login(su_user, su_password)

        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements(By.NAME, "collection_id")

        # Iterate and check search by all tags except all tag
        for i in range(1, len(checkboxes)):
            browser.find_elements(By.NAME, "collection_id")[i].click()

            element = browser.find_element(By.XPATH,
                                           "//span[contains(text(),'PH')]")

            random_phenotype = element.text
            print(random_phenotype)

            # Test with actual name
            browser.find_element(By.ID, "search").send_keys(
                random_phenotype[6:].strip())
            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()
            time.sleep(settings_cll.IMPLICTLY_WAIT)
            self.assertTrue("No phenotypes" not in browser.page_source)

            browser.find_element(By.ID, "reset-form").click()

            # Find phenotype by friendly ID (GOING to be extra feature)
            # browser.find_element(By.ID,"search").send_keys(random_phenotype[:3].strip())
            # browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()
            # self.assertTrue("No phenotypes" not in browser.page_source)
            # time.sleep(settings_cll.IMPLICTLY_WAIT)
            # browser.find_element(By.ID,"reset-form").click()

            # time.sleep(settings_cll.IMPLICTLY_WAIT)
            # Find phenotype by full name
            # browser.find_element(By.ID,"search").send_keys(random_phenotype.strip())
            # browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()
            # self.assertTrue("No phenotypes" not in browser.page_source)
            # time.sleep(settings_cll.IMPLICTLY_WAIT)
            # browser.find_element(By.ID,"reset-form").click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)
            # Find by partial name of phenotype
            self.create_test_phenotype("COVID-19 infection",
                                       "desc", [i],
                                       self.permitted_group,
                                       False,
                                       owner=self.owner_user,
                                       author="author")
            browser.find_element(By.ID, "search").send_keys("infection")
            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()
            self.assertTrue("No phenotypes" not in browser.page_source)
            browser.find_element(By.ID, "reset-form").click()
            browser.find_elements(By.NAME, "collection_id")[i].click()

    def xx_test_deleted_phenotypes(self):

        self.login(su_user, su_password)

        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        checkboxes = browser.find_elements(By.NAME, "collection_id")

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        # Iterate and check search by all tags except all tag
        for i in range(1, len(checkboxes)):
            browser.find_elements(By.NAME, "collection_id")[i].click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_element(By.ID, "show_deleted_phenotypes").click()

            browser.find_element(
                By.XPATH, '//button[@class = "btn btn-primary"]').click()


            self.assertTrue("cl-card-deleted" in
                            browser.page_source)

            browser.find_element(By.ID, "reset-form").click()

            browser.find_elements(By.NAME, "collection_id")[i].click()

    def xx_test_only_owned_phenotypes(self):

        # First login as superuser
        self.login(su_user, su_password)
        browser = self.browser
        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.ID, "show_my_phenotypes").click()

        browser.find_element(By.XPATH,
                             '//button[@class = "btn btn-primary"]').click()

        self.assertTrue("No phenotypes" in browser.page_source)

        self.logout()

        # After login to owner and check owned phenotypes
        self.login(ow_user, ow_password)
        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.ID, "show_my_phenotypes").click()

        browser.find_element(By.XPATH,
                             '//button[@class = "btn btn-primary"]').click()

        self.assertTrue("No phenotypes" not in browser.page_source)

    def xx_test_author_filter(self):

        self.login(su_user, su_password)
        browser = self.browser
        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        checkboxes = browser.find_elements(By.NAME, "collection_id")

        # Check author name with author names of phenotype
        for i in range(1, len(checkboxes)):
            browser.find_elements(By.NAME, "collection_id")[i].click()

            time.sleep(settings_cll.IMPLICTLY_WAIT)

            browser.find_element(By.NAME, "author").send_keys("test_author")

            element = [
                k for k in browser.find_elements(By.CLASS_NAME, "col-sm-12")
                if "test_author" in k.text
            ]

            for j in range(1, len(element)):
                self.assertEqual(element[j].text, "test_author")

            browser.find_elements(By.NAME, "collection_id")[i].click()

    def xx_test_phenotype_with_all_attributes(self):
        self.login(ow_user, ow_password)

        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        browser.find_elements(By.NAME, "collection_id")[0].click()

        # Test phenotype which combines all filters
        self.create_test_phenotype("test",
                                   "desc", [1, 2, 3, 4, 5, 6, 7],
                                   self.permitted_group,
                                   False,
                                   owner=self.owner_user,
                                   author="owneruser")

        browser.find_element(By.NAME, "author").send_keys("owneruser")

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.ID, "search").send_keys("test")

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.NAME, "owner").send_keys("owneruser")

        browser.find_element(By.ID, "show_my_phenotypes").click()

        browser.find_element(By.XPATH,
                             '//button[@class = "btn btn-primary"]').click()

        self.assertTrue("No phenotypes" not in browser.page_source)

    """
    NOT FOR RELEASE 1
    def test_basic_to_advanced_search(self):
        self.login(ow_user, ow_password)

        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        # Search phenotype in basic search
        browser.find_element(By.ID,"search1").send_keys("Phenotype")

        browser.find_element(By.XPATH,'//button[@classxx = "btn btn-info"]').click()

        self.assertFalse(browser.find_element(By.ID,"search1").get_attribute("value") == "")

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        # Find phenotype in advanced search and go back to basic search to check the clear input
        browser.find_element(By.XPATH,"//*[@id='show-advanced-search']").click()

        browser.find_element(By.XPATH,'//button[@class = "btn btn-primary"]').click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        self.assertTrue("No phenotypes" not in browser.page_source)

        browser.find_element(By.ID,"search").clear()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.XPATH,"//*[@id='show-basic-search']").click()

        self.assertTrue(browser.find_element(By.ID,"search1").get_attribute("value") == "")
        
        """

    def xx_test_tag_input_bar(self):
        self.login(ow_user, ow_password)

        browser = self.browser

        browser.get(self.WEBAPP_HOST + reverse('search_phenotypes'))

        browser.find_element(By.XPATH,
                             "//*[@id='show-advanced-search']").click()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.XPATH,
                             "//*[@class='bootstrap-tagsinput']").click()

        browser.find_element(By.CLASS_NAME,
                             "tt-input").send_keys("Phenotype_library")

        self.assertTrue("Nothing found." not in browser.page_source)

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.CLASS_NAME, "tt-input").clear()

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        browser.find_element(By.CLASS_NAME, "tt-input").send_keys("test")

        time.sleep(settings_cll.IMPLICTLY_WAIT)

        self.assertTrue("Nothing found." in browser.page_source)
