from datetime import datetime

from clinicalcode.models.Code import Code
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.Component import Component
from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.permissions import *
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from django.test import TestCase


class PermissionTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(PermissionTest, cls).setUpClass()
        super_user = User.objects.create_superuser(username=su_user,
                                                   password=su_password,
                                                   email=None)
        normal_user = User.objects.create_user(username=nm_user,
                                               password=nm_password,
                                               email=None)
        owner_user = User.objects.create_user(username=ow_user,
                                              password=ow_password,
                                              email=None)
        group_user = User.objects.create_user(username=gp_user,
                                              password=gp_password,
                                              email=None)

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

        cls.concept_none_can_access = Concept.objects.create(
            name="concept_noone_can_access",
            description="concept_noone_can_access",
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
            world_access=Permissions.NONE)

        cls.concept_owner_can_view = Concept.objects.create(
            name="concept_owner_can_edit",
            description="concept_owner_can_edit",
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
            owner_access=Permissions.VIEW,
            group_access=Permissions.NONE,
            world_access=Permissions.NONE)

        cls.concept_owner_can_edit = Concept.objects.create(
            name="concept_owner_can_edit",
            description="concept_owner_can_edit",
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
            owner_access=Permissions.EDIT,
            group_access=Permissions.NONE,
            world_access=Permissions.NONE)

        cls.concept_everyone_can_view = Concept.objects.create(
            name="concept_everyone_can_view",
            description="concept_view_everyone",
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
            owner_access=Permissions.NONE,
            group_access=Permissions.NONE,
            world_access=Permissions.VIEW)

        cls.concept_everyone_can_edit = Concept.objects.create(
            name="concept_everyone_can_edit",
            description="concept_everyone_can_edit",
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
            owner_access=Permissions.NONE,
            group_access=Permissions.NONE,
            world_access=Permissions.EDIT)

        cls.concept_group_can_view = Concept.objects.create(
            name="concept_group_can_view",
            description="concept_group_can_view",
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
            owner_access=Permissions.NONE,
            group_access=Permissions.VIEW,
            world_access=Permissions.NONE)

        cls.concept_group_can_edit = Concept.objects.create(
            name="concept_group_can_view",
            description="concept_group_can_view",
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
            owner_access=Permissions.NONE,
            group_access=Permissions.EDIT,
            world_access=Permissions.NONE)

        cls.workingset_none_can_access = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.NONE)

        cls.workingset_everyone_can_edit = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.EDIT)

        cls.workingset_everyone_can_view = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.NONE,
            world_access=Permissions.VIEW)

        cls.workingset_owner_can_view = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.VIEW,
            world_access=Permissions.NONE)

        cls.workingset_owner_can_edit = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.NONE,
            owner_access=Permissions.EDIT,
            world_access=Permissions.NONE)

        cls.workingset_group_can_view = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.VIEW,
            owner_access=Permissions.NONE,
            world_access=Permissions.NONE)

        cls.workingset_group_can_edit = WorkingSet.objects.create(
            name="workingset_noone_can_access",
            description="workingset_noone_can_access",
            author="the_test_goat",
            publication_doi="",
            publication_link=Google_website,
            source_reference="",
            citation_requirements="",
            concept_informations=[{"concept1": "id"}],
            created_by=super_user,
            updated_by=super_user,
            owner=owner_user,
            group=permitted_group,
            group_access=Permissions.EDIT,
            owner_access=Permissions.NONE,
            world_access=Permissions.NONE)

        cls.component_for_none = Component.objects.create(
            comment="Component visibility test",
            component_type=2,
            concept=cls.concept_none_can_access,
            created_by=owner_user,
            logical_type=2,
            name="Component")

        cls.code_list_for_none = CodeList.objects.create(
            component=cls.component_for_none,
            description="Code list visibility test")
        cls.code_for_none = Code.objects.create(
            code_list=cls.code_list_for_none,
            code="45554",
            description="visibility test")

        cls.component_for_everybody = Component.objects.create(
            comment="Component visibility test",
            component_type=2,
            concept=cls.concept_everyone_can_view,
            created_by=owner_user,
            logical_type=2,
            name="Component")

        cls.code_list_for_everybody = CodeList.objects.create(
            component=cls.component_for_everybody,
            description="Code list visibility test")
        cls.code_for_everybody = Code.objects.create(
            code_list=cls.code_list_for_everybody,
            code="24212",
            description="visibility test")

        cls.component_for_group = Component.objects.create(
            comment="Component visibility test",
            component_type=2,
            concept=cls.concept_group_can_view,
            created_by=owner_user,
            logical_type=2,
            name="Component")

        cls.code_list_for_group = CodeList.objects.create(
            component=cls.component_for_group,
            description="Code list visibility test")
        cls.code_for_group = Code.objects.create(
            code_list=cls.code_list_for_group,
            code="24212",
            description="visibility test")

    @classmethod
    def tearDownClass(cls):
        super(PermissionTest, cls).tearDownClass()

    '''
    Verify that a user with edit rights 
    who is not an owner cannot change the permissions.
    '''

    def test_normal_user_not_allowed_to_permit_con(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_permit(
            user, Concept, PermissionTest.concept_everyone_can_edit.id)
        self.assertFalse(permitted)

    def test_group_user_not_allowed_to_permit_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_permit(
            group, Concept, PermissionTest.concept_everyone_can_edit.id)
        self.assertFalse(permitted)

    '''
    Verify that a user can transfer ownership to a different user
    '''

    def test_owner_allowed_to_permit_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_permit(owner, Concept,
                                      PermissionTest.concept_owner_can_edit.id)
        self.assertTrue(permitted)

    '''
    Verify that when a new concept is created and no changes are made to the permissions, 
    only the owner can view and edit the concept.
    '''

    def test_owner_allowed_to_view_new_concept_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_new_concept_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=owner)
        self.assertTrue(permitted)

    def test_normal_user_not_allowed_to_view_new_concept_con(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=user)
        self.assertFalse(permitted)

    def test_normal_user_not_allowed_to_edit_new_concept_con(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=user)
        self.assertFalse(permitted)

    def test_group_user_not_allowed_to_view_new_concept_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=group)
        self.assertFalse(permitted)

    def test_group_user_not_allowed_to_edit_new_concept_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=group)
        self.assertFalse(permitted)

    '''
    Verify that if everyone is set to "view", 
    a different user can view the concept but not edit it.
    '''

    def test_normal_user_allowed_to_view_when_everybody_set_to_view_con(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=user)
        self.assertTrue(permitted)

    def test_normal_user_not_allowed_to_edit_when_everybody_set_to_view_con(
            self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=user)
        self.assertFalse(permitted)

    def test_group_user_allowed_to_view_when_everybody_set_to_view_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=group)
        self.assertTrue(permitted)

    def test_group_user_not_allowed_to_edit_when_everybody_set_to_view_con(
            self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=group)
        self.assertFalse(permitted)

    def test_owner_allowed_to_view_when_everybody_set_to_view_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_when_everybody_set_to_view_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=owner)
        self.assertTrue(permitted)

    '''
    Verify that if everyone is set to "edit" 
    a different user can view and edit the concept.
    '''

    def test_normal_user_allowed_to_edit_when_everybody_set_to_edit_con(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=user)
        self.assertTrue(permitted)

    def test_normal_user_allowed_to_view_when_everybody_set_to_edit_con(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=user)
        self.assertTrue(permitted)

    def test_group_user_allowed_to_edit_when_everybody_set_to_edit_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=group)
        self.assertTrue(permitted)

    def test_group_user_allowed_to_view_when_everybody_set_to_edit_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=group)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_when_everybody_set_to_edit_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_view_when_everybody_set_to_edit_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    '''
    Verify that if group is set to "view", 
    a different group member can view the concept but not edit it.
    '''

    def test_group_allowed_to_view_when_group_set_to_view_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_group_can_view.id,
                                    user=group)
        self.assertTrue(permitted)

    def test_group_not_allowed_to_edit_when_group_set_to_view_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_group_can_view.id,
                                    user=group)
        self.assertFalse(permitted)

    '''
    Verify that if group is set to "edit" 
    a different group member can view and edit the concept.
    '''

    def test_group_allowed_to_view_when_group_set_to_edit_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=group)
        self.assertTrue(permitted)

    def test_group_allowed_to_edit_when_group_set_to_edit_con(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=group)
        self.assertTrue(permitted)

    '''
    Verify that if group is set to "edit" and everyone "none", 
    a non-group member cannot view or edit.
    '''

    def test_normal_user_not_allowed_to_view_when_only_group_set_to_edit_con(
            self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=user)
        self.assertFalse(permitted)

    def test_normal_user_not_allowed_to_edit_when_only_group_set_to_edit_con(
            self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=user)
        self.assertFalse(permitted)

    def test_owner_allowed_to_view_when_only_group_set_to_edit_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_when_only_group_set_to_edit_con(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=owner)
        self.assertTrue(permitted)

    '''
    Verify that a super user can do everything, 
    regardless of permission settings.
    '''

    def test_super_user_allowed_to_permit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_permit(super_user, Concept,
                                      PermissionTest.concept_owner_can_edit.id)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_everybody_set_to_view_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_everybody_set_to_view_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_everybody_set_to_edit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_everybody_set_to_edit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            Concept,
            PermissionTest.concept_everyone_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_owner_set_to_view_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_view.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_owner_set_to_view_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_view.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_owner_set_to_edit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_owner_set_to_edit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_owner_can_edit.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_group_set_to_view_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_group_can_view.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_group_set_to_view_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_group_can_view.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_group_set_to_edit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_group_set_to_edit_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_group_can_edit.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_none_has_access_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(None,
                                    Concept,
                                    PermissionTest.concept_none_can_access.id,
                                    user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_none_has_access_con(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    PermissionTest.concept_none_can_access.id,
                                    user=super_user)
        self.assertTrue(permitted)

    '''
    -------------------------WORKINGSET TESTS--------------------------
    '''
    '''
    Verify that a user with edit rights 
    who is not an owner cannot change the permissions.
    '''

    def test_normal_user_not_allowed_to_permit_ws(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_permit(
            user, WorkingSet, PermissionTest.workingset_everyone_can_edit.id)
        self.assertFalse(permitted)

    def test_group_user_not_allowed_to_permit_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_permit(
            group, WorkingSet, PermissionTest.workingset_everyone_can_edit.id)
        self.assertFalse(permitted)

    '''
    Verify that a user can transfer ownership to a different user
    '''

    def test_owner_allowed_to_permit_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_permit(
            owner, WorkingSet, PermissionTest.workingset_owner_can_edit.id)
        self.assertTrue(permitted)

    '''
    Verify that when a new workingset is created and no changes are made to the permissions, 
    only the owner can view and edit the working set.
    '''

    def test_owner_allowed_to_view_new_workingset(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_new_workingset(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    def test_normal_user_not_allowed_to_view_new_workingset(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=user)
        self.assertFalse(permitted)

    def test_normal_user_not_allowed_to_edit_new_workingset(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=user)
        self.assertFalse(permitted)

    def test_group_user_not_allowed_to_view_new_workingset(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=group)
        self.assertFalse(permitted)

    def test_group_user_not_allowed_to_edit_new_workingset(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=group)
        self.assertFalse(permitted)

    '''
    Verify that if everyone is set to "view", 
    a different user can view the working set but not edit it.
    '''

    def test_normal_user_allowed_to_view_when_everybody_set_to_view_ws(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=user)
        self.assertTrue(permitted)

    def test_normal_user_not_allowed_to_edit_when_everybody_set_to_view_ws(
            self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=user)
        self.assertFalse(permitted)

    def test_group_user_allowed_to_view_when_everybody_set_to_view_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=group)
        self.assertTrue(permitted)

    def test_group_user_not_allowed_to_edit_when_everybody_set_to_view_ws(
            self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=group)
        self.assertFalse(permitted)

    def test_owner_allowed_to_view_when_everybody_set_to_view_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_when_everybody_set_to_view_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=owner)
        self.assertTrue(permitted)

    '''
    Verify that if everyone is set to "edit" 
    a different user can view and edit the working set.
    '''

    def test_normal_user_allowed_to_edit_when_everybody_set_to_edit_ws(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=user)
        self.assertTrue(permitted)

    def test_normal_user_allowed_to_view_when_everybody_set_to_edit_ws(self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=user)
        self.assertTrue(permitted)

    def test_group_user_allowed_to_edit_when_everybody_set_to_edit_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=group)
        self.assertTrue(permitted)

    def test_group_user_allowed_to_view_when_everybody_set_to_edit_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=group)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_when_everybody_set_to_edit_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_view_when_everybody_set_to_edit_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    '''
    Verify that if group is set to "view", 
    a different group member can view the working set but not edit it.
    '''

    def test_group_allowed_to_view_when_group_set_to_view_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_view.id,
            user=group)
        self.assertTrue(permitted)

    def test_group_not_allowed_to_edit_when_group_set_to_view_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_view.id,
            user=group)
        self.assertFalse(permitted)

    '''
    Verify that if group is set to "edit" 
    a different group member can view and edit the working set.
    '''

    def test_group_allowed_to_view_when_group_set_to_edit_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=group)
        self.assertTrue(permitted)

    def test_group_allowed_to_edit_when_group_set_to_edit_ws(self):
        group = User.objects.get(username=gp_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=group)
        self.assertTrue(permitted)

    '''
    Verify that if group is set to "edit" and everyone "none", 
    a non-group member cannot view or edit.
    '''

    def test_normal_user_not_allowed_to_view_when_only_group_set_to_edit_ws(
            self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=user)
        self.assertFalse(permitted)

    def test_normal_user_not_allowed_to_edit_when_only_group_set_to_edit_ws(
            self):
        user = User.objects.get(username=nm_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=user)
        self.assertFalse(permitted)

    def test_owner_allowed_to_view_when_only_group_set_to_edit_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    def test_owner_allowed_to_edit_when_only_group_set_to_edit_ws(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=owner)
        self.assertTrue(permitted)

    '''
    Verify that a super user can do everything, 
    regardless of permission settings.
    '''

    def test_super_user_allowed_to_permit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_permit(
            super_user, WorkingSet,
            PermissionTest.workingset_owner_can_edit.id)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_everybody_set_to_view_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_everybody_set_to_view_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_everybody_set_to_edit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_everybody_set_to_edit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_everyone_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_owner_set_to_view_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_owner_set_to_view_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_owner_set_to_edit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_owner_set_to_edit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_owner_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_group_set_to_view_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_group_set_to_view_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_view.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_group_set_to_edit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_group_set_to_edit_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_group_can_edit.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_view_when_none_has_access_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_view(
            None,
            WorkingSet,
            PermissionTest.workingset_none_can_access.id,
            user=super_user)
        self.assertTrue(permitted)

    def test_superuser_allowed_to_edit_when_none_has_access_ws(self):
        super_user = User.objects.get(username=su_user)
        permitted = allowed_to_edit(
            None,
            WorkingSet,
            PermissionTest.workingset_none_can_access.id,
            user=super_user)
        self.assertTrue(permitted)

    '''
    ------------Test visible data fetch code----------------------
    '''
    '''
        test visible code list
    '''

    def test_nornal_user_user_visible_code_list_for_none(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_codelists(normal_user, self.code_list_for_none.id)

        self.assertTrue(query.count() == 0)

    def test_nornal_user_user_visible_code_list_for_group(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_codelists(normal_user, self.code_list_for_group.id)

        self.assertTrue(query.count() == 0)

    def test_normal_user_user_visible_code_list_for_everybody(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_codelists(normal_user,
                                      self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_group_user_visible_code_list_for_none(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_codelists(group_user, self.code_list_for_none.id)

        self.assertTrue(query.count() == 0)

    def test_group_user_visible_code_list_for_group(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_codelists(group_user, self.code_list_for_group.id)

        self.assertTrue(query.count() == 1)

    def test_group_user_visible_code_list_for_everybody(self):
        group_user = User.objects.get(username=nm_user)
        query = get_visible_codelists(group_user,
                                      self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_code_list_for_none(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_codelists(owner, self.code_list_for_none.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_code_list_for_group(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_codelists(owner, self.code_list_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_code_list_for_everybody(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_codelists(owner, self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_code_list_for_none(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_codelists(super_user, self.code_list_for_none.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_code_list_for_group(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_codelists(super_user, self.code_list_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_code_list_for_everybody(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_codelists(super_user,
                                      self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    '''
        visible codes 
    '''

    def test_normal_user_visible_codes_for_none(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_codes(normal_user, self.code_list_for_none.id)

        self.assertTrue(query.count() == 0)

    def test_normal_user_visible_codes_for_group(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_codes(normal_user, self.code_list_for_group.id)

        self.assertTrue(query.count() == 0)

    def test_normal_user_visible_codes_for_everybody(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_codes(normal_user, self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_group_user_visible_codes_for_none(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_codes(group_user, self.code_list_for_none.id)

        self.assertTrue(query.count() == 0)

    def test_group_user_visible_codes_for_group(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_codes(group_user, self.code_list_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_group_user_visible_codes_for_everybody(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_codes(group_user, self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_codes_for_none(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_codes(owner, self.code_list_for_none.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_codes_for_group(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_codes(owner, self.code_list_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_codes_for_everybody(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_codes(owner, self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_codes_for_none(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_codes(super_user, self.code_list_for_none.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_codes_for_group(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_codes(super_user, self.code_list_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_codes_for_everybody(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_codes(super_user, self.code_list_for_everybody.id)

        self.assertTrue(query.count() > 0)

    '''
        visible components
    '''

    def test_normal_user_visible_components_for_none(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_components(normal_user, self.component_for_none.id)

        self.assertTrue(query.count() == 0)

    def test_normal_user_visible_components_for_group(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_components(normal_user,
                                       self.component_for_group.id)

        self.assertTrue(query.count() == 0)

    def test_normal_user_visible_components_for_everybody(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_components(normal_user,
                                       self.component_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_group_user_visible_components_for_none(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_components(group_user, self.component_for_none.id)

        self.assertTrue(query.count() == 0)

    def test_group_user_visible_components_for_group(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_components(group_user, self.component_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_group_user_visible_components_for_everybody(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_components(group_user,
                                       self.component_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_components_for_none(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_components(owner, self.component_for_none.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_components_for_group(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_components(owner, self.component_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_owner_visible_componentss_for_everybody(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_components(owner, self.component_for_everybody.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_components_for_none(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_components(super_user, self.component_for_none.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_components_for_group(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_components(super_user, self.component_for_group.id)

        self.assertTrue(query.count() > 0)

    def test_superuser_visible_components_for_everybody(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_components(super_user,
                                       self.component_for_everybody.id)

        self.assertTrue(query.count() > 0)

    '''
        visible concepts
    '''

    def test_normal_user_visible_concepts(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_concepts_live(normal_user)

        # Query should contain two concepts only (concept everybody can view and concept everybody can edit)
        self.assertTrue(query.count() == 2)
        self.assertTrue(
            (self.concept_everyone_can_view and self.concept_everyone_can_edit
             ) in query.all())

    def test_group_user_visible_concepts(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_concepts_live(group_user)

        # Query should contain four concepts only (concept everybody can view and concept everybody can edit...
        # concept group can view and concept group can edit
        self.assertTrue(query.count() == 4)
        self.assertTrue(
            (self.concept_everyone_can_view and self.concept_everyone_can_edit
             and self.concept_group_can_edit and self.concept_group_can_view
             ) in query.all())

    def test_owner_visible_concepts(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_concepts_live(owner)

        # Owner can see all of the concepts
        self.assertTrue(query.count() == 7)

    def test_superuser_visible_concepts(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_concepts_live(super_user)

        # super user can see all of the concepts
        self.assertTrue(query.count() == 7)

    '''
        visible workingset
    '''

    def test_normal_user_visible_workingsets(self):
        normal_user = User.objects.get(username=nm_user)
        query = get_visible_workingsets(normal_user)

        # Query should contain two concepts only (concept everybody can view and concept everybody can edit)
        self.assertTrue(query.count() == 2)
        self.assertTrue((self.workingset_everyone_can_view
                         and self.workingset_everyone_can_edit) in query.all())

    def test_group_user_visible_workingsets(self):
        group_user = User.objects.get(username=gp_user)
        query = get_visible_workingsets(group_user)

        # Query should contain four concepts only (concept everybody can view and concept everybody can edit...
        # concept group can view and concept group can edit
        self.assertTrue(query.count() == 4)
        self.assertTrue(
            (self.workingset_everyone_can_view and self.
             workingset_everyone_can_edit and self.workingset_group_can_view
             and self.workingset_group_can_edit) in query.all())

    def test_owner_visible_workingsets(self):
        owner = User.objects.get(username=ow_user)
        query = get_visible_workingsets(owner)

        # Owner can see all of the concepts
        self.assertTrue(query.count() == 7)

    def test_superuser_visible_workingsets(self):
        super_user = User.objects.get(username=su_user)
        query = get_visible_workingsets(super_user)

        # super user can see all of the concepts
        self.assertTrue(query.count() == 7)
