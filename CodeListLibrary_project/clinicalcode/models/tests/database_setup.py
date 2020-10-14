'''
    Database set-up for the Concept tests.
    
    Existing test suite.
'''
from datetime import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from clinicalcode.models.CodingSystem import CodingSystem
from clinicalcode.models.Concept import Concept
from clinicalcode.models.Component import Component
from clinicalcode.models.CodeList import CodeList
from clinicalcode.models.Code import Code
from clinicalcode import db_utils

def setUpTestData(cls):
    '''
        Create all the concepts, components, code lists, code regexes and codes
        to use for the concept tests (test_concepts).
    '''
    Google_website = "https://www.google.com"
    
    user = User.objects.create_user(
        username="david",
        email="d.m.bown@swansea.ac.uk",
        password="password")

    coding_system = CodingSystem.objects.create(
         name="Lookup table",
         description="Lookup Codes for testing purposes",
         link=Google_website,
         database_connection_name="default",
         table_name="clinicalcode_lookup",
         code_column_name="code",
         desc_column_name="description")
    coding_system.save()

    concept_heart_disease_1 = Concept.objects.create(
        name="Heart disease 1",
        description="Heart disease 1",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_disease_1_id = concept_heart_disease_1.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_disease_1,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="1", description="Test 1")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="11", description="Test 11")
    Code.objects.create(code_list=code_list, code="12", description="Test 12")
    Code.objects.create(code_list=code_list, code="16", description="Test 16")
    Code.objects.create(code_list=code_list, code="21", description="Test 21")
    Code.objects.create(code_list=code_list, code="24", description="Test 24")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_disease_1,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="45", description="Test 45")

    concept_heart_attack_2a = Concept.objects.create(
        name="Heart attack 2a",
        description="Heart attack 2a",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_attack_2a_id = concept_heart_attack_2a.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_attack_2a,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="2", description="Test 2")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_attack_2a,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="3", description="Test 3")

    concept_heart_failure_2b = Concept.objects.create(
        name="Heart failure 2b",
        description="Heart failure 2b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_failure_2b_id = concept_heart_failure_2b.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_failure_2b,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")
    Code.objects.create(code_list=code_list, code="12", description="Test 12")
    Code.objects.create(code_list=code_list, code="16", description="Test 16")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_failure_2b,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    concept_heart_attack_3a = Concept.objects.create(
        name="Heart attack 3a",
        description="Heart attack 3a",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_attack_3a_id = concept_heart_attack_3a.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_attack_3a,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="6", description="Test 6")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_attack_3a,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="7", description="Test 7")

    concept_heart_attack_3b = Concept.objects.create(
        name="Heart attack 3b",
        description="Heart attack 3b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_attack_3b_id = concept_heart_attack_3b.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_attack_3b,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_attack_3b,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="4", description="Test 4")

    concept_heart_failure_3a = Concept.objects.create(
        name="Heart failure 3a",
        description="Heart failure 3a",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_failure_3a_id = concept_heart_failure_3a.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_failure_3a,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")
    Code.objects.create(code_list=code_list, code="9", description="Test 9")
    Code.objects.create(code_list=code_list, code="10", description="Test 10")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_failure_3a,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="9", description="Test 9")

    concept_heart_failure_3b = Concept.objects.create(
        name="Heart failure 3b",
        description="Heart failure 3b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.concept_heart_failure_3b_id = concept_heart_failure_3b.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=concept_heart_failure_3b,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="11", description="Test 11")
    Code.objects.create(code_list=code_list, code="12", description="Test 12")
    Code.objects.create(code_list=code_list, code="13", description="Test 13")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=concept_heart_failure_3b,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="12", description="Test 12")
    Code.objects.create(code_list=code_list2, code="13", description="Test 13")

    # add the concept links
    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=concept_heart_disease_1,
        concept_ref=concept_heart_attack_2a,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 4 exclusion",
        component_type=1,
        concept=concept_heart_disease_1,
        concept_ref=concept_heart_failure_2b,
        created_by=user,
        logical_type=2,
        name="Component 4 exclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=concept_heart_attack_2a,
        concept_ref=concept_heart_attack_3a,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 4 exclusion",
        component_type=1,
        concept=concept_heart_attack_2a,
        concept_ref=concept_heart_attack_3b,
        created_by=user,
        logical_type=2,
        name="Component 4 exclusion")

    component = Component.objects.create(
        comment="Component 3 exclusion",
        component_type=1,
        concept=concept_heart_failure_2b,
        concept_ref=concept_heart_failure_3a,
        created_by=user,
        logical_type=2,
        name="Component 3 exclusion")

    component = Component.objects.create(
        comment="Component 4 inclusion",
        component_type=1,
        concept=concept_heart_failure_2b,
        concept_ref=concept_heart_failure_3b,
        created_by=user,
        logical_type=1,
        name="Component 4 inclusion")

    # test 2
    # level 1 circ system
    circ_system_1 = Concept.objects.create(
        name="Circ system 1",
        description="Circ system 1",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.circ_system_1_id = circ_system_1.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=circ_system_1,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="2", description="Test 2")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="6", description="Test 6")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")
    Code.objects.create(code_list=code_list, code="13", description="Test 13")
    Code.objects.create(code_list=code_list, code="16", description="Test 16")
    Code.objects.create(code_list=code_list, code="19", description="Test 19")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=circ_system_1,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="16", description="Test 16")
    Code.objects.create(code_list=code_list2, code="2", description="Test 2")
    # end of level 1 circ system

    # level 2 acute rheu
    acute_rheu_2a = Concept.objects.create(
        name="Acute rheu 2a",
        description="Acute rheu 2a",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.acute_rheu_2a_id = acute_rheu_2a.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=acute_rheu_2a,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=acute_rheu_2a,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="1", description="Test 1")
    # end of level 2 acute rheu

    # level 2 chronic rheu
    chronic_rheu_2b = Concept.objects.create(
        name="Chronic rheu 2b",
        description="Chronic rheu 2b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.chronic_rheu_2b_id = chronic_rheu_2b.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=chronic_rheu_2b,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="2", description="Test 2")
    Code.objects.create(code_list=code_list, code="10", description="Test 10")
    Code.objects.create(code_list=code_list, code="12", description="Test 12")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=chronic_rheu_2b,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="3", description="Test 3")
    # end of level 2 chronic rheu

    # level 2 hypertensive dis
    hypertensive_dis_2c = Concept.objects.create(
        name="hypertensive dis 2c",
        description="hypertensive dis 2c",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.hypertensive_dis_2c_id = hypertensive_dis_2c.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=hypertensive_dis_2c,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="12", description="Test 12")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")
    Code.objects.create(code_list=code_list, code="14", description="Test 14")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=hypertensive_dis_2c,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="8", description="Test 8")
    # end of level 2 hypertensive dis

    # level 3 heart inv
    heart_inv_3a = Concept.objects.create(
        name="Heart inv 3a",
        description="Heart inv 3a",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.heart_inv_3a_id = heart_inv_3a.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=heart_inv_3a,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="1", description="Test 1")
    Code.objects.create(code_list=code_list, code="6", description="Test 6")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")


    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=heart_inv_3a,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="2", description="Test 2")
    Code.objects.create(code_list=code_list2, code="7", description="Test 7")
    # end of heart inv

    # no heart inv
    no_heart_inv_3b = Concept.objects.create(
        name="No heart 3b",
        description="No heart 3b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.no_heart_inv_3b_id = no_heart_inv_3b.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=no_heart_inv_3b,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")
    Code.objects.create(code_list=code_list, code="9", description="Test 9")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=no_heart_inv_3b,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="9", description="Test 9")
    Code.objects.create(code_list=code_list2, code="12", description="Test 12")
    # end of level 3 no heart inv

    # level 3 mit dis
    mit_dis_3c = Concept.objects.create(
        name="Mit dis 3b",
        description="Mit dis 3b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.mit_dis_3c_id = mit_dis_3c.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=mit_dis_3c,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="2", description="Test 2")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="10", description="Test 10")
    Code.objects.create(code_list=code_list, code="11", description="Test 11")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=mit_dis_3c,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="5", description="Test 5")
    Code.objects.create(code_list=code_list2, code="10", description="Test 10")
    # end of level 3 mit dis

    # level 3 renal dis
    renal_dis_3d = Concept.objects.create(
        name="Renal dis 3d",
        description="Renal dis 3d",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.renal_dis_3d_id = renal_dis_3d.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=renal_dis_3d,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="6", description="Test 6")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=renal_dis_3d,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="5", description="Test 5")
    # end of level 3 renal dis

    # heart dis
    heart_dis_3e = Concept.objects.create(
        name="Heart dis 3e",
        description="Heart dis 3e",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.heart_dis_3e_id = heart_dis_3e.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=heart_dis_3e,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")
    Code.objects.create(code_list=code_list, code="12", description="Test 12")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=heart_dis_3e,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="4", description="Test 4")
    Code.objects.create(code_list=code_list2, code="5", description="Test 5")
    # end of level 3 heart dis

    # level 4 stenosis
    stenosis_4a = Concept.objects.create(
        name="stenosis 4a",
        description="stenosis 4a",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.stenosis_4a_id = stenosis_4a.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=stenosis_4a,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="6", description="Test 6")
    Code.objects.create(code_list=code_list, code="8", description="Test 8")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=stenosis_4a,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="6", description="Test 6")
    # end of level 4 stenosis

    # level 4 valve
    valve_4b = Concept.objects.create(
        name="valve 4b",
        description="valve 4b",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.valve_4b_id = valve_4b.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=valve_4b,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="1", description="Test 1")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=valve_4b,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="5", description="Test 5")
    # end of level 4 valve

    # level 4 renal fail
    fail_4c = Concept.objects.create(
        name="fail_4c",
        description="fail_4c",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.fail_4c_id = fail_4c.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=fail_4c,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="5", description="Test 5")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=fail_4c,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="8", description="Test 8")
    Code.objects.create(code_list=code_list2, code="7", description="Test 7")
    # end of level 4 renal fail

    # level 4 renal no fail
    no_fail_4d = Concept.objects.create(
        name="no_fail_4d",
        description="no_fail_4d",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.no_fail_4d_id = no_fail_4d.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=no_fail_4d,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="4", description="Test 4")
    Code.objects.create(code_list=code_list, code="7", description="Test 7")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=no_fail_4d,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="8", description="Test 8")
    # end of level 4 renal no fail

    # level 4 heart dis failure
    failure_4e = Concept.objects.create(
        name="failure_4e",
        description="failure_4e",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.failure_4e_id = failure_4e.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=failure_4e,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="9", description="Test 9")
    Code.objects.create(code_list=code_list, code="10", description="Test 10")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=failure_4e,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="10", description="Test 10")
    # end of level 4 heart dis failure

    # level 4 heart dis no fail
    no_fail_4f = Concept.objects.create(
        name="no_fail_4f",
        description="no_fail_4f",
        author="David Bown",
        entry_date=datetime.now(),
        validation_performed=True,
        validation_description="",
        #shared=1,
        publication_doi="",
        publication_link=Google_website,
        paper_published=False,
        source_reference="",
        citation_requirements="",
        #editable=1,
        created_by=user,
        modified_by=user,
        coding_system=coding_system,
        is_deleted=False)
    cls.no_fail_4f_id = no_fail_4f.id

    component = Component.objects.create(
        comment="Component 1 inclusion",
        component_type=2,
        concept=no_fail_4f,
        created_by=user,
        logical_type=1,
        name="Component 1 inclusion")

    code_list = CodeList.objects.create(component=component, description="Code list 1 inclusion")
    Code.objects.create(code_list=code_list, code="3", description="Test 3")
    Code.objects.create(code_list=code_list, code="9", description="Test 9")
    Code.objects.create(code_list=code_list, code="10", description="Test 10")

    component2 = Component.objects.create(
        comment="Component 2 exclusion",
        component_type=2,
        concept=no_fail_4f,
        created_by=user,
        logical_type=2,
        name="Component 2 exclusion")

    code_list2 = CodeList.objects.create(component=component2, description="Code list 2 exclusion")
    Code.objects.create(code_list=code_list2, code="10", description="Test 10")
    # end of level 4 heart dis  no fail

    # add the concept links
    component = Component.objects.create(
        comment="Component 4 exclusion",
        component_type=1,
        concept=circ_system_1,
        concept_ref=acute_rheu_2a,
        created_by=user,
        logical_type=2,
        name="Component 4 exclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=circ_system_1,
        concept_ref=chronic_rheu_2b,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 5 exclusion",
        component_type=1,
        concept=circ_system_1,
        concept_ref=hypertensive_dis_2c,
        created_by=user,
        logical_type=2,
        name="Component 5 exclusion")

    component = Component.objects.create(
        comment="Component 5 exclusion",
        component_type=1,
        concept=acute_rheu_2a,
        concept_ref=heart_inv_3a,
        created_by=user,
        logical_type=2,
        name="Component 5 exclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=acute_rheu_2a,
        concept_ref=no_heart_inv_3b,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=chronic_rheu_2b,
        concept_ref=mit_dis_3c,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=hypertensive_dis_2c,
        concept_ref=renal_dis_3d,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 3 exclusion",
        component_type=1,
        concept=hypertensive_dis_2c,
        concept_ref=heart_dis_3e,
        created_by=user,
        logical_type=2,
        name="Component 3 exclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=mit_dis_3c,
        concept_ref=stenosis_4a,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 3 exclusion",
        component_type=1,
        concept=mit_dis_3c,
        concept_ref=valve_4b,
        created_by=user,
        logical_type=2,
        name="Component 3 exclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=renal_dis_3d,
        concept_ref=fail_4c,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

    component = Component.objects.create(
        comment="Component 3 exclusion",
        component_type=1,
        concept=renal_dis_3d,
        concept_ref=no_fail_4d,
        created_by=user,
        logical_type=2,
        name="Component 3 exclusion")

    component = Component.objects.create(
        comment="Component 3 exclusion",
        component_type=1,
        concept=heart_dis_3e,
        concept_ref=failure_4e,
        created_by=user,
        logical_type=2,
        name="Component 3 exclusion")

    component = Component.objects.create(
        comment="Component 3 inclusion",
        component_type=1,
        concept=heart_dis_3e,
        concept_ref=no_fail_4f,
        created_by=user,
        logical_type=1,
        name="Component 3 inclusion")

        