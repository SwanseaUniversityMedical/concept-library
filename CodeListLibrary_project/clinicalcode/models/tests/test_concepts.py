#===============================================================================
# '''
#     Concept tests.
#     
#     Existing test suite.
# '''
# from datetime import datetime
# from django.test import TestCase
# from django.contrib.auth.models import User
# from clinicalcode.models.CodingSystem import CodingSystem
# from clinicalcode.models.Concept import Concept
# from clinicalcode.models.Component import Component
# from clinicalcode.models.CodeList import CodeList
# from clinicalcode.models.Code import Code
# from clinicalcode import db_utils
# 
# import database_setup
# 
# # Create your tests here.
# 
# 
# class GroupConceptCodesTestCase(TestCase):
# 
#     @classmethod
#     def setUpClass(cls):
#         super(GroupConceptCodesTestCase, cls).setUpClass()
#         print("Concept tests ...")
#         database_setup.setUpTestData(cls)
#         
#     def setup(self):
#         self.client = Client()
# 
#     def test_export_concept_codes_heart_disease_1(self):
#         print ("test_export_concept_codes_heart_disease_1")
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_disease_1_id)
# 
#         expected_result = [{'code': u'1', 'description': u'Test 1'},
#                            {'code': u'2', 'description': u'Test 2'},
#                            {'code': u'21', 'description': u'Test 21'},
#                            {'code': u'24', 'description': u'Test 24'},
#                            {'code': u'3', 'description': u'Test 3'},
#                            {'code': u'4', 'description': u'Test 4'},
#                            {'code': u'6', 'description': u'Test 6'}]
#         
#         self.assertEqual(len(codes), 7)
#         self.assertListEqual(codes, expected_result)
# 
#     def test_export_concept_codes_heart_failure_3b(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_failure_3b_id)
# 
#         expected_result = [{'code': u'11', 'description': u'Test 11'}]
# 
#         self.assertEqual(len(codes), 1, msg="Codes returned do not match")
#         self.assertListEqual(codes, expected_result)
# 
#     def test_export_concept_codes_heart_failure_3a(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_failure_3a_id)
# 
#         expected_result = [{'code': u'10', 'description': u'Test 10'},
#                            {'code': u'8', 'description': u'Test 8'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(codes, expected_result)
# 
#     def test_export_concept_codes_heart_attack_3b(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_attack_3b_id)
# 
#         expected_result = [{'code': u'5', 'description': u'Test 5'}]
# 
#         self.assertEqual(len(codes), 1, msg="Codes returned do not match")
#         self.assertListEqual(codes, expected_result)
# 
#     def test_export_concept_codes_heart_attack_3a(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_attack_3a_id)
# 
#         expected_result = [{'code': u'5', 'description': u'Test 5'},
#                            {'code': u'6', 'description': u'Test 6'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(codes, expected_result)
# 
#     def test_export_concept_codes_heart_attack_2a(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_attack_2a_id)
# 
#         expected_result = [{'code': u'2', 'description': u'Test 2'},
#                            {'code': u'6', 'description': u'Test 6'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(codes, expected_result)
# 
#     def test_export_concept_codes_heart_failure_2b(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.concept_heart_failure_2b_id)
# 
#         expected_result = [{'code': u'11', 'description': u'Test 11'},
#                            {'code': u'12', 'description': u'Test 12'},
#                            {'code': u'16', 'description': u'Test 16'}]
# 
#         self.assertEqual(len(codes), 3, msg="Codes returned do not match")
#         self.assertListEqual(codes, expected_result)
# 
#     def test_group_circ_system_1(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.circ_system_1_id)
# 
#         expected_result = [{'code': u'8', 'description': u'Test 8'},
#                            {'code': u'13', 'description': u'Test 13'},
#                            {'code': u'19', 'description': u'Test 19'},
#                            {'code': u'2', 'description': u'Test 2'},
#                            {'code': u'4', 'description': u'Test 4'},
#                            {'code': u'10', 'description': u'Test 10'},
#                            {'code': u'11', 'description': u'Test 11'},
#                            {'code': u'12', 'description': u'Test 12'}]
#         print(sorted(codes))
#         self.assertEqual(len(codes), 8)
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_acute_rheu_2a(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.acute_rheu_2a_id)
# 
#         expected_result = [{'code': u'3', 'description': u'Test 3'},
#                            {'code': u'4', 'description': u'Test 4'},
#                            {'code': u'7', 'description': u'Test 7'}]
# 
#         self.assertEqual(len(codes), 3, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_chronic_rheu_2b(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.chronic_rheu_2b_id)
# 
#         expected_result = [{'code': u'2', 'description': u'Test 2'},
#                            {'code': u'10', 'description': u'Test 10'},
#                            {'code': u'8', 'description': u'Test 8'},
#                            {'code': u'11', 'description': u'Test 11'},
#                            {'code': u'12', 'description': u'Test 12'},
#                            {'code': u'5', 'description': u'Test 5'}]
# 
#         self.assertEqual(len(codes), 6, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_hypertensive_dis_2c(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.hypertensive_dis_2c_id)
# 
#         expected_result = [{'code': u'6', 'description': u'Test 6'},
#                            {'code': u'5', 'description': u'Test 5'},
#                            {'code': u'7', 'description': u'Test 7'},
#                            {'code': u'14', 'description': u'Test 14'}]
# 
#         self.assertEqual(len(codes), 4, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_heart_inv_3a(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.heart_inv_3a_id)
# 
#         expected_result = [{'code': u'6', 'description': u'Test 6'},
#                            {'code': u'8', 'description': u'Test 8'},
#                            {'code': u'1', 'description': u'Test 1'}]
# 
#         self.assertEqual(len(codes), 3, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_no_heart_inv_3b(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.no_heart_inv_3b_id)
# 
#         expected_result = [{'code': u'7', 'description': u'Test 7'},
#                            {'code': u'8', 'description': u'Test 8'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_mit_dis_3c(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.mit_dis_3c_id)
# 
#         expected_result = [{'code': u'2', 'description': u'Test 2'},
#                            {'code': u'5', 'description': u'Test 5'},
#                            {'code': u'8', 'description': u'Test 8'},
#                            {'code': u'11', 'description': u'Test 11'}]
# 
#         self.assertEqual(len(codes), 4, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_renal_dis_3d(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.renal_dis_3d_id)
# 
#         expected_result = [{'code': u'6', 'description': u'Test 6'},
#                            {'code': u'5', 'description': u'Test 5'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_heart_dis_3e(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.heart_dis_3e_id)
# 
#         expected_result = [ {'code': u'12', 'description': u'Test 12'},
#                            {'code': u'8', 'description': u'Test 8'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_stenosis_4a(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.stenosis_4a_id)
# 
#         expected_result = [{'code': u'4', 'description': u'Test 4'},
#                            {'code': u'5', 'description': u'Test 5'},
#                            {'code': u'8', 'description': u'Test 8'}]
# 
#         self.assertEqual(len(codes), 3, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_valve_4b(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.valve_4b_id)
# 
#         expected_result = [{'code': u'3', 'description': u'Test 3'},
#                            {'code': u'1', 'description': u'Test 1'},
#                            {'code': u'4', 'description': u'Test 4'}]
# 
#         self.assertEqual(len(codes), 3, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_fail_4c(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.fail_4c_id)
# 
#         expected_result = [{'code': u'5', 'description': u'Test 5'},
#                            {'code': u'3', 'description': u'Test 3'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_no_fail_4d(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.no_fail_4d_id)
# 
#         expected_result = [{'code': u'3', 'description': u'Test 3'},
#                            {'code': u'7', 'description': u'Test 7'},
#                            {'code': u'4', 'description': u'Test 4'}]
# 
#         self.assertEqual(len(codes), 3, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_failure_4e(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.failure_4e_id)
# 
#         expected_result = [{'code': u'3', 'description': u'Test 3'},
#                            {'code': u'9', 'description': u'Test 9'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
# 
#     def test_export_concept_codes_no_fail_4f(self):
#         codes = db_utils.getGroupOfCodesByConceptId(self.no_fail_4f_id)
# 
#         expected_result = [{'code': u'3', 'description': u'Test 3'},
#                            {'code': u'9', 'description': u'Test 9'}]
# 
#         self.assertEqual(len(codes), 2, msg="Codes returned do not match")
#         self.assertListEqual(sorted(codes), sorted(expected_result))
#         
#===============================================================================