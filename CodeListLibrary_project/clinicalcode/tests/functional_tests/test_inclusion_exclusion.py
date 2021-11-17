from clinicalcode.tests.test_base import *
from clinicalcode.tests.unit_test_base import *
from clinicalcode.permissions import *
from clinicalcode.models.Concept import *
from clinicalcode.models.PublishedConcept import *
from clinicalcode.models.WorkingSet import *
from clinicalcode.models.Component import Component
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.Code import Code
from clinicalcode.models.CodeRegex import CodeRegex
from clinicalcode.views.Concept import concept_codes_to_csv
# from clinicalcode.publicsites.views import published_concept_codes_to_csv

from django.test import TestCase, TransactionTestCase
from datetime import datetime
from django.test import RequestFactory

# from cll import test_settings as settings
from cll import test_settings as settings_cll
from rest_framework.reverse import reverse

from unittest.case import skip


# @skip("skip for now")
class InclusionExclusionTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(InclusionExclusionTest, cls).setUpClass()
        cls.factory = RequestFactory()

        cls.owner_user = User.objects.create_user(
            username=ow_user, password=ow_password, email=None)

        coding_system = CodingSystem.objects.create(
            name="Lookup table",
            description="Lookup Codes for testing purposes",
            link=Google_website,
            database_connection_name="default",
            table_name="clinicalcode_lookup",
            code_column_name="code",
            desc_column_name="description")
        coding_system.save()

        '''
            level 4
            The parent is excluded child so everything should be excluded 
        '''
        '''cls.excl_level4_withexcl = Concept.objects.create(
            name="concept level 4",
            description="concept level 4",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )


        cls.excl_comp_type4_4_3 = cls.create_component_with_codes(cls, comp_type=4, log_type=1, comp_name="excluded component 5", comp_parent=cls.excl_level4_withexcl,
                                                                code_list_description="excluded code list", codes_names_list=["r2"])


        cls.level4_withexcl = Concept.objects.create(
            name="concept level 4",
            description="concept level 4",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )


        cls.excl_comp_type4_4_2 = cls.create_component_with_codes(cls, comp_type=4, log_type=2, comp_name="excluded component 5", comp_parent=cls.level4_withexcl,
                                                                code_list_description="excluded code list", codes_names_list=["r1"])

        cls.incl_level4 = Concept.objects.create(
            name="concept level 4",
            description="concept level 4",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )


        cls.incl_comp_type4_4 = cls.create_component_with_codes(cls, comp_type=4, log_type=1, comp_name="included component 5", comp_parent=cls.incl_level4,
                                                                code_list_description="included code list", codes_names_list=["i9", "i10"])

        cls.excl_comp_type4_4 = cls.create_component_with_codes(cls, comp_type=4, log_type=2, comp_name="excluded component 5", comp_parent=cls.incl_level4,
                                                                code_list_description="included code list", codes_names_list=["i10"])'''

        '''
            level 3
        '''
        ''''cls.incl_level3 = Concept.objects.create(
            name="concept level 3",
            description="concept level 3",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )

        cls.excl_child_component_4_2 = cls.create_component_with_codes(cls, comp_type=1, log_type=2, comp_name="excluded child concept 5_2", comp_parent=cls.incl_level3,
                                                                     code_list_description="included code list", codes_names_list=[], concept_ref=cls.excl_level4_withexcl,
                                                                     concept_ref_history_id=cls.excl_level4_withexcl.history.first().history_id)   

        cls.incl_child_component_4_2 = cls.create_component_with_codes(cls, comp_type=1, log_type=1, comp_name="included child concept 5_2", comp_parent=cls.incl_level3,
                                                                     code_list_description="included code list", codes_names_list=[], concept_ref=cls.level4_withexcl,
                                                                     concept_ref_history_id=cls.level4_withexcl.history.first().history_id)      

        cls.incl_child_component_4 = cls.create_component_with_codes(cls, comp_type=1, log_type=1, comp_name="included child concept 5", comp_parent=cls.incl_level3,
                                                                     code_list_description="included code list", codes_names_list=[], concept_ref=cls.incl_level4,
                                                                     concept_ref_history_id=cls.incl_level4.history.first().history_id)       

        cls.incl_comp_type3_3 = cls.create_component_with_codes(cls, comp_type=3, log_type=1, comp_name="included component 4", comp_parent=cls.incl_level3,
                                                                code_list_description="included code list", codes_names_list=["i7", "i8"])

        cls.excl_comp_type3_3 = cls.create_component_with_codes(cls, comp_type=3, log_type=2, comp_name="excluded component 4", comp_parent=cls.incl_level3,
                                                                code_list_description="excluded code list", codes_names_list=["i2"])'''

        '''
            level 2
        '''
        '''cls.level2 = Concept.objects.create(
            name="concept level 2",
            description="concept level 2",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )   

        cls.incl_child_component_3 = cls.create_component_with_codes(cls, comp_type=1, log_type=1, comp_name="included child concept 4", comp_parent=cls.level2,
                                                                     code_list_description="included code list", codes_names_list=[], concept_ref=cls.incl_level3,
                                                                     concept_ref_history_id=cls.incl_level3.history.first().history_id)

        cls.incl_comp_type2_2 = cls.create_component_with_codes(cls, comp_type=2, log_type=1, comp_name="included component 3", comp_parent=cls.level2,
                                                                code_list_description="included code list", codes_names_list=["e6", "e7", "ic9"])

        cls.excl_comp_type2_2 = cls.create_component_with_codes(cls, comp_type=2, log_type=2, comp_name="excluded component 3", comp_parent=cls.level2,
                                                                code_list_description="excluded code list", codes_names_list=["e6", "e7", "i5"])'''

        '''
            level 1
        '''
        cls.level1 = Concept.objects.create(
            name="concept level 1",
            description="concept level 1",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )

        '''cls.incl_child_component_2 = cls.create_component_with_codes(cls, comp_type=1, log_type=1, comp_name="included child concept 3", comp_parent=cls.level1,
                                                                     code_list_description="included code list", codes_names_list=[], concept_ref=cls.level2,
                                                                     concept_ref_history_id=cls.level2.history.first().history_id)
        
        cls.incl_comp_type2_1 = cls.create_component_with_codes(cls, comp_type=2, log_type=1, comp_name="included component 2", comp_parent=cls.level1,
                                                                code_list_description="included code list", codes_names_list=["i4", "i5", "i6"])

        cls.excl_comp_type2_1 = cls.create_component_with_codes(cls, comp_type=2, log_type=2, comp_name="excluded component 2", comp_parent=cls.level1,
                                                                code_list_description="excluded code list", codes_names_list=["e3", "e4"])

        cls.incl_comp_type3_1 = cls.create_component_with_codes(cls, comp_type=3, log_type=1, comp_name="included component 2", comp_parent=cls.level1,
                                                                code_list_description="included code list", codes_names_list=["e3", "e4", "i6", "ic4", "ic5"])

        cls.excl_comp_type3_1 = cls.create_component_with_codes(cls, comp_type=3, log_type=2, comp_name="excluded component 2", comp_parent=cls.level1,
                                                                code_list_description="excluded code list", codes_names_list=["i6"])

        cls.incl_comp_type4_1 = cls.create_component_with_codes(cls, comp_type=4, log_type=1, comp_name="included component 2", comp_parent=cls.level1,
                                                                code_list_description="included code list", codes_names_list=["ic6", "ic7", "ic8"])

        cls.excl_comp_type4_1 = cls.create_component_with_codes(cls, comp_type=4, log_type=2, comp_name="excluded component 2", comp_parent=cls.level1,
                                                                code_list_description="excluded code list", codes_names_list=["ic3", "ic8"])'''

        '''
            root
        '''
        cls.root = Concept.objects.create(
            name="root",
            description="root",
            author="the_test_goat",
            entry_date=datetime.now(),
            validation_performed=True,
            validation_description="",
            publication_doi="",
            publication_link=Google_website,
            paper_published=False,
            source_reference="",
            citation_requirements="",
            created_by=cls.owner_user,
            modified_by=cls.owner_user,
            coding_system=coding_system,
            is_deleted=False,
            owner=cls.owner_user,
            group_access=Permissions.EDIT,
            owner_access=Permissions.EDIT,
            world_access=Permissions.EDIT
        )

        cls.incl_child_component_1 = cls.create_component_with_codes(cls, comp_type=1, log_type=1,
                                                                     comp_name="included child concept",
                                                                     comp_parent=cls.root,
                                                                     code_list_description="included code list",
                                                                     codes_names_list=["i100", "i200", "i300"],
                                                                     concept_ref=cls.level1,
                                                                     concept_ref_history_id=cls.level1.history.first().history_id)

        cls.excl_child_component_1 = cls.create_component_with_codes(cls, comp_type=1, log_type=2,
                                                                     comp_name="excluded child concept",
                                                                     comp_parent=cls.root,
                                                                     code_list_description="included code list",
                                                                     codes_names_list=["i300"], concept_ref=cls.level1,
                                                                     concept_ref_history_id=cls.level1.history.first().history_id)

        cls.incl_comp_type2 = cls.create_component_with_codes(cls, comp_type=2, log_type=1,
                                                              comp_name="included component", comp_parent=cls.root,
                                                              code_list_description="included code list",
                                                              codes_names_list=["i1", "i2", "i3"])

        cls.excl_comp_type2 = cls.create_component_with_codes(cls, comp_type=2, log_type=2,
                                                              comp_name="excluded component", comp_parent=cls.root,
                                                              code_list_description="excluded code list",
                                                              codes_names_list=["i1", "e2"])

        cls.incl_comp_type3 = cls.create_component_with_codes(cls, comp_type=3, log_type=1,
                                                              comp_name="included component", comp_parent=cls.root,
                                                              code_list_description="included code list",
                                                              codes_names_list=["ic1", "ic2"])

        cls.excl_comp_type3 = cls.create_component_with_codes(cls, comp_type=3, log_type=2,
                                                              comp_name="excluded component", comp_parent=cls.root,
                                                              code_list_description="excluded code list",
                                                              codes_names_list=["ic2", "ec1"])

        cls.incl_comp_type4 = cls.create_component_with_codes(cls, comp_type=4, log_type=1,
                                                              comp_name="included component", comp_parent=cls.root,
                                                              code_list_description="included code list",
                                                              codes_names_list=["ic3", "ic4"])

        cls.excl_comp_type4 = cls.create_component_with_codes(cls, comp_type=4, log_type=2,
                                                              comp_name="excluded component", comp_parent=cls.root,
                                                              code_list_description="excluded code list",
                                                              codes_names_list=["ic4"])

        cls.root.save()

        cls.output = ['i2', 'i3', 'ic1', 'ic3', 'i100', 'i200']

        '''published concept'''
        cls.root_history_id = cls.root.history.first().history_id
        cls.published_root = PublishedConcept.objects.create(concept=cls.root,
                                                             concept_history_id=cls.root_history_id,
                                                             created_by=cls.owner_user)

    @classmethod
    def tearDownClass(cls):
        super(InclusionExclusionTest, cls).tearDownClass()

    # Returns logical type of component and list of codes 
    # Concept ref for reference to the child concept (optional)
    @staticmethod
    def create_component_with_codes(self, comp_type, log_type, comp_name, comp_parent, code_list_description,
                                    codes_names_list, concept_ref=None, concept_ref_history_id=None):
        component = Component.objects.create(
            component_type=comp_type,
            concept=comp_parent,
            created_by=self.owner_user,
            logical_type=log_type,
            name=comp_name)

        # if component type is child concept add reference to the child
        if comp_type == 1:
            component.concept_ref = concept_ref
            component.concept_ref_history_id = concept_ref_history_id

        code_list = CodeList.objects.create(
            component=component, description=code_list_description)
        list_of_codes = []

        if comp_type != 1 and comp_type != 2:
            codeRegex = CodeRegex.objects.create(
                component=component, regex_type=1, regex_code="%i%", code_list=code_list)

        for name in codes_names_list:
            code = Code.objects.create(
                code_list=code_list, code=name, description=name)
            code.save()
            list_of_codes.append(code.code)

        code_list.save()
        component.save()
        comp_parent.save()

        return log_type, list_of_codes

    def get_codes_from_response(self, response):
        response = response.splitlines()
        response.pop(0)  # remove headers

        codes = []

        for r in response:
            code = r.split(",")[0]
            codes.append(code)

        # sort both lists
        codes.sort()
        self.output.sort()
        print(("EXPECTED OUTPUT: ", self.output))
        print(("RESPONSE_CODES: ", codes))

        return codes

    def test_root(self):
#         url = ('%s%s%s' % ('/concepts/C',
#                            self.root.id, '/export/codes'))

        url = reverse('concept_codes_to_csv', kwargs={'pk': self.root.id}) 
                
        request = self.factory.get(url)
        request.user = self.owner_user
        request.CURRENT_BRAND = ''
        
        response = concept_codes_to_csv(request, self.root.id)

        response_codes = self.get_codes_from_response(response.content)

        expected_output = self.output

        self.assertEqual(response_codes, expected_output,
                         "response codes and expected output are not equal")

    def test_published(self):
        if settings_cll.ENABLE_PUBLISH:
            from clinicalcode.views.Concept import history_concept_codes_to_csv

#             url = ('%s%s%s%s%s' % ('/concepts/C', self.published_root.concept_id
#                                    , '/version/', self.published_root.concept_history_id
#                                    , '/export/codes'))
        
            url = reverse('history_concept_codes_to_csv'
                                               , kwargs={'pk': self.published_root.concept_id,
                                                         'concept_history_id': self.published_root.concept_history_id}) 
            request = self.factory.get(url)
            request.user = self.owner_user
            request.CURRENT_BRAND = ''

            response = history_concept_codes_to_csv(request, self.published_root.concept_id,
                                                    self.published_root.concept_history_id)

            response_codes = self.get_codes_from_response(response.content)

            expected_output = self.output

            self.assertEqual(response_codes, expected_output,
                             "response codes and expected output are not equal")
