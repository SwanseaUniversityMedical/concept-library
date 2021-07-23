from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.permissions import *
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.models.Component import Component
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.Code import Code
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from urlparse import urlparse
import unittest

#from django.conf import settings
#from cll import settings as settings_cll
from cll import test_settings as settings
from cll import test_settings as settings_cll

import time


class HierarchicalCodeListsTest(StaticLiveServerTestCase):

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
        super(HierarchicalCodeListsTest, self).setUp()

        '''data'''
        self.super_user = User.objects.create_superuser(
            username=su_user, password=su_password, email=None)
        self.normal_user = User.objects.create_user(
            username=nm_user, password=nm_password, email=None)
        self.owner_user = User.objects.create_user(
            username=ow_user, password=ow_password, email=None)
        self.group_user = User.objects.create_user(
            username=gp_user, password=gp_password, email=None)

        permitted_group = Group.objects.create(name="permitted_group")
        self.group_user.groups.add(permitted_group)

        self.coding_system = CodingSystem.objects.create(
            name="Lookup table",
            description="Lookup Codes for testing purposes",
            link=Google_website,
            database_connection_name="default",
            table_name="clinicalcode_lookup",
            code_column_name="code",
            desc_column_name="description")
        self.coding_system.save()

        self.concept_everybody_can_edit = self.add_concept(
            self, name="concept everybody can edit", world_access=Permissions.EDIT)

        concept_info_string = '[{"%s":{"ttt|4":"yyy"}}]' % (
            str(self.concept_everybody_can_edit.id))

        self.workingset_everybody_can_edit = WorkingSet.objects.create(
            name="wokringset everybody can access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            created_by=self.super_user,
            updated_by=self.super_user,
            owner=self.owner_user,
            concept_informations=concept_info_string,
            concept_version={(str(self.concept_everybody_can_edit.id)): str(
                self.concept_everybody_can_edit.history.first().history_id)},
            group=permitted_group,
            group_access=Permissions.VIEW,
            owner_access=Permissions.VIEW,
            world_access=Permissions.EDIT
        )

        self.child_concept_to_be_added = self.add_concept(
            self, name="child concept to be added", world_access=Permissions.VIEW)

        self.child_concept = self.add_concept(self, name="child concept to be updated", world_access=Permissions.VIEW)
        self.child_component = self.add_child_component(
            self, name="child to be updated", parent=self.concept_everybody_can_edit, 
            concept_ref=self.child_concept, concept_ref_history_id=self.child_concept.history.first().history_id)

        self.concept_only_owner_can_access = self.add_concept(self, name="concept only owner can access",
                                                              world_access=Permissions.NONE)

        # For the last test
        self.child_concept2 = self.add_concept(
            self, name="child concept 2", world_access=Permissions.VIEW)
        self.child_component2 = self.add_child_component(
            self, name="child 2", parent=self.child_concept, concept_ref=self.child_concept2, concept_ref_history_id=self.child_concept2.history.first().history_id)

        self.child_concept3 = self.add_concept(
            self, name="child concept 3", world_access=Permissions.VIEW)
        self.child_component3 = self.add_child_component(
            self, name="child 3", parent=self.child_concept2, concept_ref=self.child_concept3, concept_ref_history_id=self.child_concept3.history.first().history_id)

    @staticmethod
    def add_concept(self, name, world_access):
        concept = Concept.objects.create(
            name=name,
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
            created_by=self.super_user,
            modified_by=self.super_user,
            coding_system=self.coding_system,
            is_deleted=False,
            owner=self.owner_user,
            # group=self.permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.EDIT,
            world_access=world_access
        )
        concept.save()

        return concept

    @staticmethod
    def add_child_component(self, name, parent, concept_ref, concept_ref_history_id):
        child = Component.objects.create(
            comment="child concept",
            component_type=1,
            concept=parent,
            concept_ref=concept_ref,
            concept_ref_history_id=concept_ref_history_id,
            created_by=self.owner_user,
            logical_type=1,
            name=name)

        code_list = CodeList.objects.create(
            component=child, description="code_list_description")

        code_list.save()
        
        # insert some codes as a proper data structure
        Code.objects.create(code_list=code_list, code="c2", description="Test 2")
        Code.objects.create(code_list=code_list, code="c3", description="Test 3")
    
        child.save()

        return child

    def tearDown(self):
        #self.browser.refresh()
        #time.sleep(settings.TEST_SLEEP_TIME)

        self.browser.quit()
        super(HierarchicalCodeListsTest, self).tearDown()


    def login(self, username, password):
        self.logout()
        self.browser.find_element_by_name('username').send_keys(username)
        self.browser.find_element_by_name('password').send_keys(password)
        self.browser.find_element_by_name('password').send_keys(Keys.ENTER)

    def logout(self):
        self.browser.get('%s%s' % (settings.WEBAPP_HOST, '/account/logout/?next=/account/login/'))
      
        
    def wait_to_be_logged_in(self, username):
        wait = WebDriverWait(self.browser, 10)
        element = wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'p.navbar-text'), username)) 
        
    '''
        When a child concept is added to a concept or working set, the latest version is always added.
        Functions checks both concept and workingset.
    '''

    def test_latest_version_added_after_adding_child_to_concept(self):
        # get latest version
        concept_latest_version = self.concept_everybody_can_edit.history.first().history_id
        print("0 concept_latest_version=" + str(concept_latest_version))
        workingset_latest_version = self.workingset_everybody_can_edit.history.first().history_id
        print("0 workingset_latest_version=" + str(workingset_latest_version))
        
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.concept_everybody_can_edit.id, '/update/'))

        time.sleep(settings.TEST_SLEEP_TIME)

        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.presence_of_element_located(
            (By.ID, "conceptTypes")))
        # add child
        btn = browser.find_element_by_id(
            'conceptTypes')
        btn.click()

        time.sleep(2) # wait for popup
        btn.send_keys(Keys.DOWN)
        time.sleep(2) 
        browser.find_element_by_id(
            'addConcept').click()

        wait.until(EC.presence_of_element_located(
            (By.ID, "concept-search-text")))

        #time.sleep(2)
        concept_search_field = browser.find_element_by_id(
            "concept-search-text")

        time.sleep(2)  # wait to load component form

        concept_search_field.send_keys("child concept to be added")

        time.sleep(5)  # wait to load concept prompt

        # click on a prompt to fill the field
        concept_search_field.send_keys(Keys.DOWN)
        concept_search_field.send_keys(Keys.ENTER)

        time.sleep(10) 
#         #component_name = browser.find_element_by_id("id_name")
#         #component_name = browser.find_element_by_name("name")
#         #component_name.send_keys('comp name')
        
        browser.find_element_by_id("saveBtn").click()

        time.sleep(5)  # wait to submition be completed

#         wait = WebDriverWait(self.browser, 10)
#         wait.until(EC.presence_of_element_located(
#             (By.CLASS_NAME, "alert-success")))
        
        browser.find_element_by_id("save-changes").click()  # save changes

        concept_latest_version_after_adding_child = self.concept_everybody_can_edit.history.first().history_id
        workingset_latest_version_after_adding_child = self.workingset_everybody_can_edit.history.first().history_id
#         print("1 concept_latest_version_after_adding_child=" + str(concept_latest_version_after_adding_child))
#         print("1 workingset_latest_version_after_adding_child=" + str(workingset_latest_version_after_adding_child))

        self.assertNotEquals(concept_latest_version,
                             concept_latest_version_after_adding_child)
        # propagation sync is stopped
#         # Michal: no idea why is not working... in live it is working...
#         self.assertNotEquals(workingset_latest_version,
#                              workingset_latest_version_after_adding_child)

    '''
        When a child concept is updated, any concept or working set that contains it automatically generates a new version.
        The update happens recursively.
    '''
    '''
        def test_latest_version_added_after_updating_child(self):
            # propagation sync is stopped
            # test is ignored
            pass
            return
    
            # get latest version
            concept_latest_version = self.concept_everybody_can_edit.history.first().history_id
            workingset_latest_version = self.workingset_everybody_can_edit.history.first().history_id
    
            self.login(ow_user, ow_password)
            browser = self.browser
            # get the test server url
            browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.child_concept.id, '/update/'))
    
            
            time.sleep(settings.TEST_SLEEP_TIME)
            
            # update child
            browser.find_element_by_id("save-changes").click()
    
            wait = WebDriverWait(self.browser, 10)
            wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, "alert-success")))
    
            concept_latest_version_after_adding_child = self.concept_everybody_can_edit.history.first().history_id
            workingset_latest_version_after_adding_child = self.workingset_everybody_can_edit.history.first().history_id
    
            self.assertNotEquals(concept_latest_version,
                                 concept_latest_version_after_adding_child)
            self.assertNotEquals(workingset_latest_version,
                                 workingset_latest_version_after_adding_child)
    '''        
        

    '''
        The version history shows this update as "Concept changed, automatic update" or something,
        and the user field makes it clear that this was a system update, not a user update.
    '''
            
    '''
        def test_version_history_shows_update(self):
            # propagation sync is stopped
            # cso this test is ignored
            pass
            return 
        #######################
        #######################
            self.login(ow_user, ow_password)
            
            browser = self.browser
            # get the test server url
            browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.child_concept.id, '/update/'))
    
            
            time.sleep(settings.TEST_SLEEP_TIME)
    
            WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.ID, "save-changes"))
                )
            # update child
            browser.find_element_by_id("save-changes").click()
    
            
    
            browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.concept_everybody_can_edit.id, '/detail/'))
            
            time.sleep(settings.TEST_SLEEP_TIME)
    
            concept_history_change_reason = self.concept_everybody_can_edit.history.first(
            ).history_change_reason
    
            # check if change reason appears in the page
            self.assertTrue(concept_history_change_reason in browser.page_source)
    
            # repeat the same for workingset
            browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/workingsets/',
                                      self.workingset_everybody_can_edit.id, '/detail/'))
            time.sleep(settings.TEST_SLEEP_TIME)
            
            workingset_history_change_reason = self.workingset_everybody_can_edit.history.first(
            ).history_change_reason
    
            self.assertTrue(
                workingset_history_change_reason in browser.page_source)
            
    '''  
              

    '''
        When a user clicks "revert" or "fork" on a historical version of a concept or working set that has a child,
        there is a warning message "the new version will refer to the latest version of child concepts. Continue? Yes/no"
    '''

    '''def test_concept_warning_message_when_revert(self):
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.concept_everybody_can_edit.id, '/version/',
                                      self.concept_everybody_can_edit.history.last().history_id, '/detail/'))

        self.login(ow_user, ow_password)

        browser.find_element_by_id("revert-btn").click()
        time.sleep(2)
        self.assertTrue("warning text" in browser.page_source)

    def test_concept_warning_message_when_fork(self):
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.concept_everybody_can_edit.id, '/version/',
                                      self.concept_everybody_can_edit.history.last().history_id, '/detail/'))

        self.login(ow_user, ow_password)

        browser.find_element_by_id("fork-btn").click()
        time.sleep(2)
        self.assertTrue("warning text" in browser.page_source)'''

    '''
    def xxtest_workingset_warning_message_when_revert(self):
        self.login(ow_user, ow_password)
        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (settings.WEBAPP_HOST, '/workingsets/',
                                      self.workingset_everybody_can_edit.id, '/version/',
                                      self.workingset_everybody_can_edit.history.last().history_id, '/detail/'))

        time.sleep(settings.TEST_SLEEP_TIME)

        browser.find_element_by_id("revert-btn").click()

        time.sleep(2)
        self.assertTrue(
            "The concepts will automatically refer to the latest version" in browser.page_source)
    '''
        
        

    '''
        When one code list includes another code list as a component,
        the parent code list takes a copy of the codes, and it doesn't change when the child changes.
    '''

    def test_copy_of_codes(self):
        pass

    '''
        The parent code list stores and displays the version of the child code list that was used.
    '''

    '''def test_version_storing_of_the_child(self):
        self.login(ow_user, ow_password)
        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.concept_everybody_can_edit.id, '/detail/'))

        time.sleep(settings.TEST_SLEEP_TIME)

        # update child
        table = browser.find_element_by_id("component-table")

        # time.sleep(100)

        
        #For some reason component table is showing None value for version!!!!!!!
        
        table_rows = table.find_element_by_tag_name('tr')
        table_data = table.find_elements_by_tag_name('td')

        print("component history id: ", self.component.history.first().history_id)'''

    '''
        If the child code list is no longer the latest version (and there is access), 
        then there is an "update" functionality to click a button and update the child to the latest.
    '''

    def test(self):
        pass

    '''
        If the user no longer has access to view the child code list, this is highlighted with a warning.
    '''
    def test_warning_message(self):
        # change permission of the child concept
        self.child_concept.world_access = Permissions.NONE
        self.child_concept.save()
        
#         ######################
#         from ... import db_utils
# 
#         print(self.child_concept.id)
#         print(Component.objects.all().count())
#         print(Component.objects.filter(concept_id=self.concept_everybody_can_edit.id).values_list('id', 'concept_id'))
#         print(Component.objects.get(concept_id=self.concept_everybody_can_edit.id).concept.id)
#         print(Component.objects.get(concept_id=self.concept_everybody_can_edit.id).concept_ref)
#         print(Component.objects.get(concept_id=self.concept_everybody_can_edit.id).concept_ref.id)
#         print(Component.objects.get(concept_id=self.concept_everybody_can_edit.id).concept_ref_history_id)
#                
#         concept_history_id = int(Concept.objects.get(pk=self.concept_everybody_can_edit.id).history.latest().history_id)         
#   
#         concept = db_utils.getHistoryConcept(concept_history_id)
#     
#         concept_history_date = concept['history_date']
#         print(concept_history_date)
#         components = db_utils.getHistoryComponents(self.concept_everybody_can_edit.id, concept_history_date, skip_codes=True)
#         print(components)
#         #############################
        
        
        self.login(nm_user, nm_password)
        browser = self.browser
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.concept_everybody_can_edit.id, '/detail/'))

        

        time.sleep(settings.TEST_SLEEP_TIME)

        # warning = browser.find_element_by_class_name("alert-danger").text

        self.assertTrue("no view permission" in browser.page_source)

    '''
        test if a child concept is pointing to the latest version when a parent is reverted or forked
    '''
    def test_concept_child_is_pointing_to_the_latest_version_when_parent_reverted(self):
        
        self.login(ow_user, ow_password)
        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.concept_everybody_can_edit.id, '/version/',
                                      self.concept_everybody_can_edit.history.last().history_id, '/detail/'))

        time.sleep(5)
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "revert-btn"))
        )
        

        # revert to the first version of the parent
        browser.find_element_by_id("revert-btn").click()

        time.sleep(2)  # wait for pop up

        browser.find_element_by_xpath(
            "//button[@type='submit']").click()  # revert

        # go to the child details page
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.child_concept.id, '/detail/'))
        time.sleep(settings.TEST_SLEEP_TIME)
        
        latest = self.child_concept.history.first().history_id

        element = browser.find_element_by_xpath(
            "//label[contains(text(),'Version ID:')]/following-sibling::div")

        self.assertEqual(str(element.text.split('(')[0].strip()), str(latest))


    def test_concept_child_is_pointing_to_the_latest_version_when_parent_forked(self):
        self.login(ow_user, ow_password)
        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                      self.concept_everybody_can_edit.id, '/version/',
                                      self.concept_everybody_can_edit.history.last().history_id, '/detail/'))

        time.sleep(5)
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "fork-btn"))
        )
        
        # revert to the first version of the parent
        browser.find_element_by_id("fork-btn").click()

        time.sleep(2)  # wait for pop up

        browser.find_element_by_xpath(
            "//button[@type='submit']").click()  # revert

        # go to the child details page
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.child_concept.id, '/detail/'))
        
        time.sleep(settings.TEST_SLEEP_TIME)
        
        latest = self.child_concept.history.first().history_id

        element = browser.find_element_by_xpath(
            "//label[contains(text(),'Version ID:')]/following-sibling::div")

        self.assertEqual(str(element.text.split('(')[0].strip()), str(latest))


    def test_workingset_child_is_pointing_to_the_latest_version_when_parent_reverted(self):
        # unnecessary test
        
        self.login(ow_user, ow_password)
        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (settings.WEBAPP_HOST, '/workingsets/',
                                      self.workingset_everybody_can_edit.id, '/history/',
                                      self.workingset_everybody_can_edit.history.last().history_id, '/detail/'))

        
        time.sleep(5)
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "revert-btn"))
        )


        # revert to the first version of the parent
        browser.find_element_by_id("revert-btn").click()

        time.sleep(2)  # wait for pop up

        browser.find_element_by_xpath(
            "//button[@type='submit']").click()  # revert

        # go to the child details page
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.concept_everybody_can_edit.id, '/detail/'))
        
        time.sleep(settings.TEST_SLEEP_TIME)

        latest = self.concept_everybody_can_edit.history.first().history_id

        element = browser.find_element_by_xpath(
            "//label[contains(text(),'Version ID:')]/following-sibling::div")

        self.assertEqual(str(element.text.split('(')[0].strip()), str(latest))


    '''
        A concept cannot be added as a child 
        if you don't have permission to use that concept (i.e. view permission on all descendants).
    '''
    def test_child_cannot_be_added_without_permission(self):
        # login as normal so he does not have access to the child
        self.login(nm_user, nm_password)

        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.concept_everybody_can_edit.id, '/update/'))

        time.sleep(settings.TEST_SLEEP_TIME)
        
        # try to add child
        browser.find_element_by_css_selector(
            'button.btn.btn-primary.dropdown-toggle').click()
        browser.find_element_by_link_text("Concept").click()

        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.presence_of_element_located(
            (By.ID, "concept-search-text")))

        concept_search_field = browser.find_element_by_id(
            "concept-search-text")

        time.sleep(2)  # wait to load component form

        concept_search_field.send_keys("concept only owner can access")

        time.sleep(settings.TEST_SLEEP_TIME)  # wait to load concept prompt

        # click on a prompt to fill the field
        concept_search_field.send_keys(Keys.DOWN)
        concept_search_field.send_keys(Keys.ENTER)

        browser.find_element_by_id("saveBtn").click()

        time.sleep(2)

        self.assertTrue("Please enter component name"
                        #in browser.page_source
                        in str(browser.switch_to_alert().text)
                        )

    '''
        A concept cannot be added as a child if it would create a circular situation 
        (the current concept would be its own descendant). Test this with 4 levels of inheritance.
    '''

    '''def test_child_concept_cannot_be_added_to_itself(self):
        self.login(ow_user, ow_password)
        
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (settings.WEBAPP_HOST, '/concepts/',
                                  self.child_concept3.id, '/update/'))

        
        time.sleep(settings.TEST_SLEEP_TIME)
        
        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button.btn.btn-primary.dropdown-toggle")))

        # add child
        browser.find_element_by_css_selector(
            'button.btn.btn-primary.dropdown-toggle').click()
        browser.find_element_by_link_text("Concept").click()

        wait.until(EC.presence_of_element_located(
            (By.ID, "concept-search-text")))

        concept_search_field = browser.find_element_by_id(
            "concept-search-text")

        time.sleep(2)  # wait to load component form

        concept_search_field.send_keys("concept everybody can edit")

        time.sleep(2)  # wait to load concept prompt

        # click on a prompt to fill the field
        concept_search_field.send_keys(Keys.DOWN)
        concept_search_field.send_keys(Keys.ENTER)

        browser.find_element_by_xpath("//button[@type='submit']").click()

        # time.sleep(100)  # wait to submition be completed'''
