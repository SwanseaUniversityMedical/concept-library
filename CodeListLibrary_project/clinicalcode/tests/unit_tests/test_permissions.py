# '''
#     Unit Tests for Permissions
# 
#     For deciding who gets to access what.
# '''
# 
# from django.test import TestCase
# # Test system imports specifically for these tests.
# from clinicalcode.tests.test_base import *
# from clinicalcode.tests.unit_test_base import *
# from clinicalcode.permissions import *
# # Additional imports to support these tests.
# from clinicalcode.models.Concept import *
# # Additional imports to support test database creation.
# from datetime import datetime
# 
# 
# class PermissionTest(TestCase):
#     
#     def test_permission_values(self):
#         '''
#             Check that the values to be used in the database are expected and
#             make sure that if they are changed, this test asks that that is
#             correct.
#             !!! This is intentional constants checking.
#         '''
#         self.assertEqual(Permissions.NONE, 1)
#         self.assertEqual(Permissions.VIEW, 2)
#         self.assertEqual(Permissions.EDIT, 3)
# 
# 
#     def allowed_to_view_concept(self, user_name, user_password, concept):
#         user = User.objects.get(username=user_name);
#         login = self.client.login(username=user_name, password=user_password)
#         self.assertTrue(login)
#         permitted = allowed_to_view(user, Concept, concept)
#         return permitted
# 
# 
#     def allowed_to_edit_concept(self, user_name, user_password, concept):
#         user = User.objects.get(username=user_name);
#         login = self.client.login(username=user_name, password=user_password)
#         self.assertTrue(login)
#         permitted = allowed_to_edit(user, Concept, concept)
#         return permitted
# 
# 
#     def test_concept_view_permissions(self):
#         '''
#             Test Concept view permission.
#             - that we must be logged-in
#             - that a superuser can always access a Concept
#             - that we can only access as the owner if we have View/Edit
#               permission
#             - that we can only access as the group-member if we belong to a
#               group with View/Edit permission
#             - that we can only access as the otherwise if everyone has
#               View/Edit permission           
#             - that we are allowed to view if we have edit permission           
#         '''
#         def test_not_allowed_to_view_when_not_loggedin(self):
#             user = User.objects.get(username=nm_user);
#             self.client.logout()
#             permitted = allowed_to_view(user, Concept,
#                             PermissionTest.concept_noone_can_access.id)
#             self.assertFalse(permitted)
#             
#         def test_allowed_to_view_when_everyone_is(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(gp_user, gp_password,
#                     PermissionTest.concept_everyone_can_view.id))
#             
#         def test_allowed_to_view_when_in_group(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(gp_user, gp_password,
#                     PermissionTest.concept_group_can_view.id))
#             
#         def test_not_allowed_to_view_when_not_in_group(self):
#             self.assertFalse(
#                 self.allowed_to_view_concept(nm_user, nm_password,
#                     PermissionTest.concept_group_can_view.id))
#             self.assertFalse(
#                 self.allowed_to_view_concept(ow_user, ow_password,
#                     PermissionTest.concept_group_can_view.id))
#             
#         def test_allowed_to_view_when_owner(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(ow_user, ow_password,
#                     PermissionTest.concept_owner_can_view.id))
#             
#         def test_not_allowed_to_view_when_not_owner(self):
#             self.assertFalse(
#                 self.allowed_to_view_concept(nm_user, nm_password,
#                     PermissionTest.concept_owner_can_view.id))
#             self.assertFalse(
#                 self.allowed_to_view_concept(gp_user, gp_password,
#                     PermissionTest.concept_owner_can_view.id))
#             
#         def test_allowed_to_view_when_superuser(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_noone_can_access.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_owner_can_view.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_group_can_view.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_owner_and_group_can_view.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_owner_can_view.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_group_can_view.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_group_and_owner_can_view.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_can_view.id))
# 
#             
#         print"test_concept_view_permissions"
#         test_not_allowed_to_view_when_not_loggedin(self)
#         test_allowed_to_view_when_everyone_is(self)
#         test_allowed_to_view_when_superuser(self)
#         test_allowed_to_view_when_in_group(self)
#         test_not_allowed_to_view_when_not_in_group(self)
#         test_allowed_to_view_when_owner(self)
#         test_not_allowed_to_view_when_not_owner(self)
# 
#     def test_concept_view_with_edit_permissions(self):
#         '''
#             Test Concept view access with edit permission.
#             Same tests as for view access with view permission but with
#             concepts that have EDIT rather than VIEW permission.
#         '''
#         def test_allowed_to_view_when_everyone_is(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(gp_user, gp_password,
#                     PermissionTest.concept_everyone_can_edit.id))
#             
#         def test_allowed_to_view_when_in_group(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(gp_user, gp_password,
#                     PermissionTest.concept_group_can_edit.id))
#             
#         def test_not_allowed_to_view_when_not_in_group(self):
#             self.assertFalse(
#                 self.allowed_to_view_concept(nm_user, nm_password,
#                     PermissionTest.concept_group_can_edit.id))
#             self.assertFalse(
#                 self.allowed_to_view_concept(ow_user, ow_password,
#                     PermissionTest.concept_group_can_edit.id))
#             
#         def test_allowed_to_view_when_owner(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(ow_user, ow_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             
#         def test_not_allowed_to_view_when_not_owner(self):
#             self.assertFalse(
#                 self.allowed_to_view_concept(nm_user, nm_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             self.assertFalse(
#                 self.allowed_to_view_concept(gp_user, gp_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             
#         def test_allowed_to_view_when_superuser(self):
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_group_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_owner_and_group_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_owner_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_group_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_group_and_owner_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_view_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_can_edit.id))
# 
#             
#         print"test_concept_view_with_edit_permissions"
#         test_allowed_to_view_when_everyone_is(self)
#         test_allowed_to_view_when_superuser(self)
#         test_allowed_to_view_when_in_group(self)
#         test_not_allowed_to_view_when_not_in_group(self)
#         test_allowed_to_view_when_owner(self)
#         test_not_allowed_to_view_when_not_owner(self)
#         
#     def test_concept_edit_permissions(self):
#         '''
#             Test Concept edit permission.
#             Same tests as for view permission except that we are testing that
#             we are allowed to edit with concepts with EDIT permission.
#             Add tests that we are not allowed to edit the VIEW permitted
#             concepts.
#         '''
#         def test_not_allowed_to_edit_when_not_loggedin(self):
#             user = User.objects.get(username=nm_user);
#             self.client.logout()
#             permitted = allowed_to_edit(user, Concept,
#                             PermissionTest.concept_noone_can_access.id)
#             self.assertFalse(permitted)
#             
#         def test_allowed_to_edit_when_everyone_is(self):
#             self.assertTrue(
#                 self.allowed_to_edit_concept(gp_user, gp_password,
#                     PermissionTest.concept_everyone_can_edit.id))
#             
#         def test_not_allowed_to_edit_when_everyone_can_view(self):
#             self.assertFalse(
#                 self.allowed_to_edit_concept(gp_user, gp_password,
#                     PermissionTest.concept_everyone_can_view.id))
#             
#         def test_allowed_to_edit_when_in_group(self):
#             self.assertTrue(
#                 self.allowed_to_edit_concept(gp_user, gp_password,
#                     PermissionTest.concept_group_can_edit.id))
#             
#         def test_not_allowed_to_edit_when_in_group_can_view(self):
#             self.assertFalse(
#                 self.allowed_to_edit_concept(gp_user, gp_password,
#                     PermissionTest.concept_group_can_view.id))
#             
#         def test_not_allowed_to_edit_when_in_view_group(self):
#             self.assertFalse(
#                 self.allowed_to_edit_concept(vgp_user, vgp_password,
#                     PermissionTest.concept_group_can_edit.id))
#             
#         def test_not_allowed_to_edit_when_not_in_group(self):
#             self.assertFalse(
#                 self.allowed_to_edit_concept(nm_user, nm_password,
#                     PermissionTest.concept_group_can_edit.id))
#             self.assertFalse(
#                 self.allowed_to_edit_concept(ow_user, ow_password,
#                     PermissionTest.concept_group_can_edit.id))
#             
#         def test_allowed_to_edit_when_owner(self):
#             self.assertTrue(
#                 self.allowed_to_edit_concept(ow_user, ow_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             
#         def test_not_allowed_to_edit_when_owner_can_view(self):
#             self.assertFalse(
#                 self.allowed_to_edit_concept(ow_user, ow_password,
#                     PermissionTest.concept_owner_can_view.id))
#             
#         def test_not_allowed_to_edit_when_not_owner(self):
#             self.assertFalse(
#                 self.allowed_to_edit_concept(nm_user, nm_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             self.assertFalse(
#                 self.allowed_to_edit_concept(gp_user, gp_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             
#         def test_allowed_to_edit_when_superuser(self):
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_noone_can_access.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_owner_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_group_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_owner_and_group_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_owner_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_group_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_and_group_and_owner_can_edit.id))
#             self.assertTrue(
#                 self.allowed_to_edit_concept(su_user, su_password,
#                     PermissionTest.concept_everyone_can_edit.id))
# 
#             
#         print"test_concept_edit_permissions"
#         test_not_allowed_to_edit_when_not_loggedin(self)
#         test_allowed_to_edit_when_everyone_is(self)
#         test_allowed_to_edit_when_in_group(self)
#         test_not_allowed_to_edit_when_not_in_group(self)
#         test_allowed_to_edit_when_owner(self)
#         test_not_allowed_to_edit_when_owner_can_view(self)
#         test_not_allowed_to_edit_when_not_owner(self)
#         test_allowed_to_edit_when_superuser(self)
#         test_not_allowed_to_edit_when_everyone_can_view(self)    
#         test_not_allowed_to_edit_when_in_group_can_view(self)
#         
#     def test_not_allowed_to_edit_when_not_loggedin(self):
#         user = User.objects.get(username=nm_user);
#         self.client.logout()
#         response = self.client.get('/')
#         permitted = allowed_to_edit(user, Concept,
#                         PermissionTest.concept_noone_can_access.id)
#         self.assertFalse(permitted)
# 
# 
#     def test_not_allowed_to_edit_when_normaluser(self):
#         user = User.objects.get(username=nm_user);
#         login = self.client.login(username=nm_user, password=nm_password)
#         self.assertTrue(login)
#         response = self.client.get('/')
#         permitted = allowed_to_edit(user, Concept, 
#                         PermissionTest.concept_noone_can_access.id)
#         self.client.logout()
#         self.assertFalse(permitted)
# 
# 
#     def test_allowed_to_edit_when_superuser(self):
#         user = User.objects.get(username=su_user);
#         login = self.client.login(username=su_user, password=su_password)
#         self.assertTrue(login)
#         response = self.client.get('/')
#         permitted = allowed_to_edit(user, Concept,
#                         PermissionTest.concept_noone_can_access.id)
#         self.client.logout()
#         self.assertTrue(permitted)
# 
#     """
#     def test_not_allowed_to_edit_when_normaluser(self):
#         user = User.objects.get(username=nm_user);
#         login = self.client.login(username=nm_user, password=nm_password)
#         self.assertTrue(login)
#         response = self.client.get('/')
#         permitted = allowed_to_edit(user, Concept,
#                         PermissionTest.concept_noone_can_access.id)
#         self.client.logout()
#         self.assertFalse(permitted)
#     """
# 
#     """
#         base_url = 'http://localhost:8000'
#         login_url = base_url + '/account/login?next=/'
#         su_user = 'pete'
#         su_password = 'geiriauwedieillyncu'
#         user = 'pete.arnold'
#         password = 'llyncugeiriau'
#         test_urls = ['/concepts', '/workingset',
#                      '/concepts/200/detail', '/concepts/200/update']
#         test_api_urls = ['/api']
#             
#         @wait
#         def wait_to_be_redirected_to_signin(self):
#             print "Waiting for redirection ... ", self.login_url
#             signinbar = self.browser.find_element_by_css_selector('div.panel-title')
#             print signinbar.text
#             self.assertIn('Sign In', signinbar.text)
#             
#             
#         @wait
#         def wait_to_be_redirected_to_api_noauth(self):
#             print "Waiting for redirection to unauthorised API page ... "
#             noauth_json = self.browser.find_elements_by_css_selector('.str')
#             self.assertEqual(len(noauth_json), 2)
#             print noauth_json.text[1]
#             self.assertIn('"Authentication credentials were not provided."', noauth_json.text[1])
#             
#             
#         @wait
#         def wait_to_be_logged_in(self, username):
#             print "Waiting for login ... ", self.login_url
#             navbar = self.browser.find_element_by_css_selector('p.navbar-text')
#             print navbar.text
#             self.assertIn(username, navbar.text)
#             
#     
#         def log_inout(self, username, password):
#             self.wait_to_be_redirected_to_signin()
#             
#             self.browser.find_element_by_name('username').send_keys(username)
#             self.browser.find_element_by_name('password').send_keys(password)
#             self.browser.find_element_by_name('password').send_keys(Keys.ENTER)
#             
#             self.wait_to_be_logged_in(username)
#             
#             self.browser.find_element_by_class_name('navbar-link').click()
#             
#             self.wait_to_be_redirected_to_signin()
#             
#             
#         def can_log_inout_superuser(self):
#             print "Permissions:unit-tests:test_can_log_inout_superuser."
#             print "Logging in as ", self.su_user , ", ", self.su_password, " to ", self.login_url       
#             self.browser.get(self.login_url)     
#             self.log_inout(self.su_user, self.su_password)
#             
#             
#         def can_log_inout_normaluser(self):
#             print "Permissions:unit-tests:test_can_log_inout_normaluser."
#             print "Logging in as ", self.user , ", ", self.password, " to ", self.login_url
#             self.browser.get(self.login_url)     
#             self.log_inout(self.user, self.password)
#     
#     
#         def no_access_when_not_logged_in(self, urls):
#             print "Permissions:unit-tests:no_access_when_not_logged_in."
#             for url in urls:
#                 print "Checking ", self.base_url + url
#                 self.browser.get(self.base_url + url)
#                 self.wait_to_be_redirected_to_signin()
#     
#         def no_access_to_api_when_not_logged_in(self, apiurls):
#             print "Permissions:unit-tests:no_access_to_api_when_not_logged_in."
#             for apiurl in apiurls:
#                 print "Checking ", self.base_url + apiurl
#                 self.browser.get(self.base_url + apiurl)
#                 self.wait_to_be_redirected_to_api_noauth()
#     
#     
#         def test_loginout(self):
#             '''
#                 Test the ability to log in and out.
#                 (1) Check that a super-user can log-in and out.
#                 (2) Check that a normal-user can log-in and out.
#                 (n) Check that access to a page produces the sign-in page if logged
#                     out.
#             '''
#             self.can_log_inout_superuser()
#             self.can_log_inout_normaluser()
#             self.no_access_when_not_logged_in(self.test_urls)
#             self.no_access_to_api_when_not_logged_in(self.test_api_urls)
#             
#             '''
#             (1) parameters: user, set-class, set-id.
#                 variables: user is SU; user is in a group
#                 Check that a non-user, ordinary user and admin user work
#                 Check that concepts and working-sets work
#                     check with a concept/working-set with all types of permission is/is not visible and/or editable
#                 Check that good set-ids and bad set-ids work
#             '''
#             # There's a concept 'Can_be_viewed_by_everyone'.
#             # There's a user 'Not_authenticated'.
#             # The user cannot view the concept.
#             #self.fail('test_allowed_to_view failed!')
#     """
# 
#     def setUp(self):
#         # Set-up access to the test database.
#         pass
#         
# 
#     @classmethod
#     def setUpTestData(cls):
#         '''
#             !!! Move this to test_base.
#             Create all the users, concepts, components, code lists, code
#             regexes and codes to use within the test database.
#         '''
#         print "Permission Unit Tests"
#         # Users: a normal user and a super_user.
#         super_user = User.objects.create_superuser(username=su_user, password=su_password, email=None)
#         normal_user = User.objects.create_user(username=nm_user, password=nm_password, email=None)
#         owner_user = User.objects.create_user(username=ow_user, password=ow_password, email=None)
#         group_user = User.objects.create_user(username=gp_user, password=gp_password, email=None)
#         view_group_user = User.objects.create_user(username=vgp_user, password=vgp_password, email=None)
#         edit_group_user = User.objects.create_user(username=egp_user, password=egp_password, email=None)
#         
#         # Groups: a group that is not permitted and one that is.
#         permitted_group = Group.objects.create(name="permitted_group")
#         forbidden_group = Group.objects.create(name="forbidden_group")
#         view_group = Group.objects.create(name="view_group")
#         edit_group = Group.objects.create(name="edit_group")
#         # Add the group to the group-user's groups.
#         group_user.groups.add(permitted_group)
#         view_group_user.groups.add(view_group)
#         edit_group_user.groups.add(edit_group)
#         
#         coding_system = CodingSystem.objects.create(
#              name="Lookup table",
#              description="Lookup Codes for testing purposes",
#              link=Google_website,
#              database_connection_name="default",
#              table_name="clinicalcode_lookup",
#              code_column_name="code",
#              desc_column_name="description")
#         coding_system.save()
# 
#         # Concepts with various view characteristics.
#         '''
#             Owner    Group    Everyone
#             No       No       No        noone
#             Yes      No       No        owner
#             No       Yes      No        group
#             Yes      Yes      No        owner+group
#             No       No       Yes       everyone
#             Yes      No       Yes       owner+everyone
#             No       Yes      Yes       group+everyone
#             Yes      Yes      Yes       owner+group+everyone
#         '''
#         cls.concept_noone_can_access = Concept.objects.create(
#             name="concept_noone_can_access",
#             description="concept_noone_can_access",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             group_access=Permissions.NONE,
#             owner_access=Permissions.NONE,
#             world_access=Permissions.NONE
#         )
#         
#         cls.concept_owner_can_view = Concept.objects.create(
#             name="concept_owner_can_view",
#             description="concept_owner_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.VIEW,
#             group_access=Permissions.NONE,
#             world_access=Permissions.NONE
#         )
#         
#         cls.concept_group_can_view = Concept.objects.create(
#             name="concept_group_can_view",
#             description="concept_group_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.NONE,
#             group_access=Permissions.VIEW,
#             world_access=Permissions.NONE
#         )
# 
#         cls.concept_owner_and_group_can_view = Concept.objects.create(
#             name="concept_owner_and_group_can_view",
#             description="concept_owner_and_group_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.VIEW,
#             group_access=Permissions.VIEW,
#             world_access=Permissions.NONE
#         )
# 
#         cls.concept_everyone_can_view = Concept.objects.create(
#             name="concept_everyone_can_view",
#             description="concept_everyone_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.NONE,
#             group_access=Permissions.NONE,
#             world_access=Permissions.VIEW
#         )
#         
#         cls.concept_everyone_and_owner_can_view = Concept.objects.create(
#             name="concept_everyone_and_owner_can_view",
#             description="concept_everyone_and_owner_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.VIEW,
#             group_access=Permissions.NONE,
#             world_access=Permissions.VIEW
#         )
#         
#         cls.concept_everyone_and_group_can_view = Concept.objects.create(
#             name="concept_everyone_and_group_can_view",
#             description="concept_everyone_and_group_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.NONE,
#             group_access=Permissions.VIEW,
#             world_access=Permissions.VIEW
#         )
#         
#         cls.concept_everyone_and_group_and_owner_can_view = Concept.objects.create(
#             name="concept_everyone_and_group_and_owner_can_view",
#             description="concept_everyone_and_group_and_owner_can_view",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.VIEW,
#             group_access=Permissions.VIEW,
#             world_access=Permissions.VIEW
#         )
#         
#         cls.concept_owner_can_edit = Concept.objects.create(
#             name="concept_owner_can_edit",
#             description="concept_owner_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.EDIT,
#             group_access=Permissions.NONE,
#             world_access=Permissions.NONE
#         )
#         
#         cls.concept_group_can_edit = Concept.objects.create(
#             name="concept_group_can_edit",
#             description="concept_group_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.NONE,
#             group_access=Permissions.EDIT,
#             world_access=Permissions.NONE
#         )
# 
#         cls.concept_owner_and_group_can_edit = Concept.objects.create(
#             name="concept_owner_and_group_can_edit",
#             description="concept_owner_and_group_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.EDIT,
#             group_access=Permissions.EDIT,
#             world_access=Permissions.NONE
#         )
# 
#         cls.concept_everyone_can_edit = Concept.objects.create(
#             name="concept_everyone_can_edit",
#             description="concept_everyone_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.NONE,
#             group_access=Permissions.NONE,
#             world_access=Permissions.EDIT
#         )
#         
#         cls.concept_everyone_and_owner_can_edit = Concept.objects.create(
#             name="concept_everyone_and_owner_can_edit",
#             description="concept_everyone_and_owner_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.EDIT,
#             group_access=Permissions.NONE,
#             world_access=Permissions.EDIT
#         )
#         
#         cls.concept_everyone_and_group_can_edit = Concept.objects.create(
#             name="concept_everyone_and_group_can_edit",
#             description="concept_everyone_and_group_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.NONE,
#             group_access=Permissions.EDIT,
#             world_access=Permissions.EDIT
#         )
#         
#         cls.concept_everyone_and_group_and_owner_can_edit = Concept.objects.create(
#             name="concept_everyone_and_group_and_owner_can_edit",
#             description="concept_everyone_and_group_and_owner_can_edit",
#             author="the_test_goat",
#             entry_date=datetime.now(),
#             validation_performed=True,
#             validation_description="",
#             publication_doi="",
#             publication_link=Google_website,
#             paper_published=False,
#             source_reference="",
#             citation_requirements="",
#             created_by=super_user,
#             modified_by=super_user,
#             coding_system=coding_system,
#             is_deleted=False,
#             owner=owner_user,
#             group=permitted_group,
#             owner_access=Permissions.EDIT,
#             group_access=Permissions.EDIT,
#             world_access=Permissions.EDIT
#         )
#         