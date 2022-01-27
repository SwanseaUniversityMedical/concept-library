import sys
from datetime import datetime
from unittest import skip, skipIf

from clinicalcode.models.Concept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.permissions import *
from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from decouple import Config, RepositoryEnv
from django.conf import settings
from django.test import TestCase, override_settings

''' 
    If arguments does not contain read_only substring then skip the test
    because it means that read only settings are not used and tests will fail.
    See manage.py to see how it works.
'''


@skipIf('read_only' not in sys.argv[-1], "READ ONLY TEST SKIPPED")
class ReadOnlyTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        # Users: a normal user and a super_user.
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
        view_group_user = User.objects.create_user(username=vgp_user,
                                                   password=vgp_password,
                                                   email=None)
        edit_group_user = User.objects.create_user(username=egp_user,
                                                   password=egp_password,
                                                   email=None)

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

        cls.concept_everybody_can_edit = Concept.objects.create(
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
            world_access=Permissions.EDIT)

    '''
    A concept owner cannot edit.
    '''

    def test_owner_not_allowed_to_edit(self):
        owner = User.objects.get(username=ow_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    ReadOnlyTest.concept_everybody_can_edit.id,
                                    user=owner)
        self.assertFalse(permitted)

    '''
    A user cannot create a new concept.
    '''

    def test_user_not_allowed_to_create(self):
        permitted = allowed_to_create()
        self.assertFalse(permitted)

    '''
    A super user CANNOT create, edit, revert, or fork a concept.
    '''

    def test_super_user_not_allowed_to_edit(self):
        super = User.objects.get(username=su_user)
        permitted = allowed_to_edit(None,
                                    Concept,
                                    ReadOnlyTest.concept_everybody_can_edit.id,
                                    user=super)
        self.assertFalse(permitted)
