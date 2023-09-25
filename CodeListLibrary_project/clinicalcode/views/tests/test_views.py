from unittest.case import skip
from django.test import Client, TestCase

from ...utils import (detect_sql_meta_characters, detect_sql_injection_with_keywords)

@skip("just skip")
class ViewTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(ViewTest, cls).setUpClass()
        print("View tests ...")

    def setup(self):
        self.client = Client()

    def test_sqlInjection_sqlMetaCharacters_provideMatch(self):
        value = 'SELECT --:\''
        match = detect_sql_meta_characters(value)
        self.assertEqual(match, True)

    def test_sqlInjection_noSqlMetaCharacters_doesNotProvideMatch(self):
        value = 'C08'
        match = detect_sql_meta_characters(value)
        self.assertEqual(match, False)

    def test_sqlInject_sqlWithKeywords_provideMatch(self):
        value = "' select"

        match = detect_sql_injection_with_keywords(value)
        self.assertEqual(match, True)

    def test_sqlInject_sqlWithoutKeywords_doesNotProvideMatch(self):
        value = "C09"
        match = detect_sql_injection_with_keywords(value)
        self.assertEqual(match, False)
