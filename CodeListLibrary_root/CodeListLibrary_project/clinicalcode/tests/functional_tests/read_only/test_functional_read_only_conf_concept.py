from django.test import override_settings, modify_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.permissions import *
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from decouple import Config, RepositoryEnv
from selenium.common.exceptions import NoSuchElementException
from os.path import dirname
from unittest import skip, skipIf
import sys

# from django.conf import settings
# from cll import read_only_test_settings
from cll import test_settings as settings
from cll import read_only_test_settings

from django.contrib.auth import logout
import time

''' 
    If arguments does not contain read_only substring then skip the test
    because it means that read only settings are not used and tests will fail.
    See manage.py to see how it works.
'''
@skipIf('read_only' not in sys.argv[-1], "READ ONLY TEST SKIPPED")   
class ReadOnlyTestConcept(StaticLiveServerTestCase):
    
    def setUp(self):
        # settings for gitlab running
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        location = dirname(dirname(__file__)) 
        if settings.IS_LINUX:
            self.browser = webdriver.Chrome(os.path.join(location, "chromedriver"), chrome_options=chrome_options)
        else:
            self.browser = webdriver.Chrome(os.path.join(location, "chromedriver.exe"), chrome_options=chrome_options)
        super(ReadOnlyTestConcept, self).setUp()
        
        
        '''data'''
        super_user = User.objects.create_superuser(username=su_user, password=su_password, email=None)
        normal_user = User.objects.create_user(username=nm_user, password=nm_password, email=None)
        owner_user = User.objects.create_user(username=ow_user, password=ow_password, email=None)
        group_user = User.objects.create_user(username=gp_user, password=gp_password, email=None)
        view_group_user = User.objects.create_user(username=vgp_user, password=vgp_password, email=None)
        edit_group_user = User.objects.create_user(username=egp_user, password=egp_password, email=None)
        
        # Groups: a group that is not permitted and one that is.
        permitted_group = Group.objects.create(name="permitted_group")
        forbidden_group = Group.objects.create(name="forbidden_group")
        view_group = Group.objects.create(name="view_group")
        edit_group = Group.objects.create(name="edit_group")
        # Add the group to the group-user's groups.
        group_user.groups.add(permitted_group)
        view_group_user.groups.add(view_group)
        edit_group_user.groups.add(edit_group)
        
        
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
            name="concept_everybody_can_edit",
            description="concept_everybody_can_edit",
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
            world_access=Permissions.EDIT
        )
        
        
    def tearDown(self):
        self.browser.quit()
        super(ReadOnlyTestConcept, self).tearDown()    
    
    
    def login(self, username, password):
        self.logout()
        self.browser.find_element_by_name('username').send_keys(username)
        self.browser.find_element_by_name('password').send_keys(password)
        self.browser.find_element_by_name('password').send_keys(Keys.ENTER)
      
    def logout(self):
        self.browser.get('%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/account/logout/?next=/account/login/'))
      
        
    def wait_to_be_logged_in(self, username):
        wait = WebDriverWait(self.browser, 10)
        element = wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'p.navbar-text'), username))  

    '''
    A user cannot revert a concept.
    ''' 
    def test_normal_user_cannot_revert(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/detail/'))
        
        time.sleep(3)
        #self.wait_to_be_logged_in(nm_user)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('revert-btn')
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
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/revert/'))
        
        time.sleep(3)
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
    
    
    def test_owner_cannot_revert(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/detail/'))
        
        time.sleep(3)
             
        exist = True
        try:
            button = self.browser.find_element_by_id('revert-btn')
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
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/revert/'))
        
        time.sleep(3)
             
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
        
    
    '''
    A user cannot fork a concept.
    '''
    def test_normal_user_cannot_fork_in_detail(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/detail/'))
        
        time.sleep(3)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('fork-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
        
    def test_normal_user_cannot_fork_through_url(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/fork/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
    
    def test_normal_user_cannot_fork_in_hisotry(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/detail/'))
        
        time.sleep(3)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('fork-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
        
    def test_normal_user_cannot_fork_through_history_url(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/revert/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
    
    
    def test_owner_cannot_fork_in_detail(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/detail/'))
        
        time.sleep(3)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('fork-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
    
    def test_owner_cannot_fork_through_url(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/fork/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
    
    def test_owner_cannot_fork_in_history(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/detail/'))
        
        time.sleep(3)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('fork-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
        
    def test_owner_cannot_fork_through_history_url(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/revert/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
    
    '''
    A super user CANNOT create, edit, revert, or fork a working set.
    '''
    def test_super_user_cannot_create(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/create/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
        
    def test_super_user_cannot_edit(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                              self.concept_everybody_can_edit.id, '/update/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
  
  
    def test_super_user_cannot_revert(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/detail/'))
        
        time.sleep(3)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('revert-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
        
    def test_super_user_cannot_revert_through_url(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/revert/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
           
    
    def test_super_user_cannot_fork_in_detail(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/detail/'))
        
        time.sleep(3)
        #self.wait_to_be_logged_in(su_user)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('fork-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
        
    def test_super_user_cannot_fork_through_url(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/fork/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
    
    def test_super_user_cannot_fork_in_hisotry(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/detail/'))
        
        time.sleep(3)
        
        exist = True
        try:
            button = self.browser.find_element_by_id('fork-btn')
            is_disabled = button.get_attribute("disabled")
            self.assertTrue(is_disabled)
            return True
        except NoSuchElementException:
            exist = False
            
        self.assertFalse(exist)
        
        
    def test_super_user_cannot_fork_through_history_url(self):
        self.login(su_user, su_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                                self.concept_everybody_can_edit.id, '/history/', 
                                self.concept_everybody_can_edit.history.first().history_id, '/revert/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
    
    
    '''
    A user cannot edit by creating their own URL string to bypass the interface.
    '''
    def test_normal_user_cannot_edit_by_own_url(self):
        self.login(nm_user, nm_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                              self.concept_everybody_can_edit.id, '/update/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
        
    def test_owner_cannot_edit_by_own_url(self):
        self.login(ow_user, ow_password)
        browser = self.browser
        # get the test server url
        browser.get('%s%s%s%s' % (self.live_server_url.replace('localhost', '127.0.0.1'), '/concepts/', 
                              self.concept_everybody_can_edit.id, '/update/'))
        
        time.sleep(3)
        
        self.assertTrue("403: Permission denied" in browser.page_source or 
                        "500: Page unavailable" in browser.page_source)
        
        