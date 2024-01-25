from cll.test_settings import WEBAPP_HOST

"""
Conftest contants
"""
ENTITY_CLASS_FIELDS = {"name": "Phenotype",
                       "description": "A phenotype defines how an event or state related "
                                      "to health is measured in data.",
                       "entity_prefix": "PH"}

TEMPLATE_FIELDS = {"name": "Clinical-Coded Phenotype",
                   "description": "Phenotype definitions that are based on lists of "
                                  "clinical codes, or algorithms using clinical codes.",
                   "template_version": 1}

TEMPLATE_JSON_V1_PATH = "dynamic_templates/clinical_coded_phenotype.json"

TEMPLATE_DATA = {
                      "sex": "1",
                      "type": "1",
                      "version": 1,
                      "coding_system": [],
                      "event_date_range": "",
                      "concept_information": []
                }

"""
Constants for test_template_versions
"""
TEMPLATE_JSON_V2_PATH = 'clinicalcode/tests/constants/test_template.json'
API_LINK = "/api/v1/templates/1/detail/"
CREATE_PHENOTYPE_TEMPLATE_PATH = "clinicalcode/tests/constants/create_phenotype_template.yaml"
TEST_CREATE_PHENOTYPE_PATH = "clinicalcode/tests/constants/test_create_phenotype.yaml"
PHENOTYPE_ATTR_KEYS = ("phenotype_version_id", "phenotype_id")
NEW_FIELDS = ['Primary Clinical Trial', 'Endorsement Organisation', 'Endorsement Date', 'Regulatory Approval Study',
              'Regulatory Approval organisation', 'Regulatory Approval Date']
TEMPLATE_DATA_V2 = {
                        "sex": "1",
                        "type": "1",
                        "version": 2,
                        "coding_system": [],
                        "endorsement_date": "24/01/2024",
                        "event_date_range": "",
                        "concept_information": [],
                        "primary_clinical_trial": "2",
                        "endorsement_organisation": "",
                        "regulatory_approval_date": "24/01/2024",
                        "regulatory_approval_study": "",
                        "regulatory_approval_organisation": ""
                    }
