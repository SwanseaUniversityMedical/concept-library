from datetime import datetime
from django.urls import reverse
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser

import re
import json
import pytest

from clinicalcode.views.Publish import Publish, RequestPublish

@pytest.mark.django_db
class TestPublishing:

    def __build_http_request(self, user, url='', resolver_name='', resolver_kwargs=None, method='GET'):
        host = re.compile(r'https?://')
        host = host.sub('', str(url)).strip().strip('/')

        request = HttpRequest()
        request.user = user
        request.META = { 'HTTP_HOST': host, 'SERVER_NAME': host }
        request.path = url + reverse(resolver_name, kwargs=resolver_kwargs)
        request.method = method
        request.session = { }
        request.IS_HDRUK_EXT = '0'
        request.CURRENT_BRAND = ''

        return request

    @pytest.mark.unit_test
    @pytest.mark.parametrize('user_type,entity_status', [
        (None, 'ANY'),
        ('normal_user', 'ANY'),
        ('owner_user', 'ANY'),
        ('moderator_user', 'ANY'),
    ])
    def test_publish_request_get(self, generate_entity_session, user_type, entity_status, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_entity_session['users'].get(user_type)
        else:
            user = AnonymousUser()
            user_type = 'Anonymous'

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        entity_id = entity.id
        entity_history_id = entity.history.first().history_id
        entity_kwargs = { 'pk': entity_id, 'history_id': entity_history_id }

        request = self.__build_http_request(
            user,
            url=live_server,
            method='GET',
            resolver_name='generic_entity_request_publish',
            resolver_kwargs=entity_kwargs
        )

        # validate response code
        expected_status_code = 302 if user_type == 'Anonymous' else 200

        response = RequestPublish.as_view()(request, **entity_kwargs)
        assert response.status_code == expected_status_code, \
               f'Status code mismatch, expected {expected_status_code} but got {response.status_code} for {user_type}'

        # validate content if applicable
        if response.status_code != 200:
            return

        try:
            result = json.loads(response.content)

            assert result.get('entity_type') == 'Phenotype', \
                'Mismatch on %s\'s PublishRequest, expected %s/%d to be \'Phenotype\' but got %s' % (
                    user_type, entity_id, entity_history_id, str(result.get('entity_type'))
                )

            assert result.get('entity_id') == entity_id, \
                'Mismatch on %s\'s PublishRequest, expected ID as %s but got %s' % (
                    user_type, entity_id, str(result.get('entity_id'))
                )

            assert result.get('entity_history_id') == entity_history_id, \
                'Mismatch on %s\'s PublishRequest, expected HistoryID as %d but got %s' % (
                    user_type, entity_history_id, str(result.get('entity_history_id'))
                )

            assert result.get('allowed_to_publish') == (user_type != 'normal_user'), \
                'Mismatch on %s\'s PublishRequest, expected to be able to publish %s/%d but got %s' % (
                    user_type, entity_id, entity_history_id, str(result.get('entity_type'))
                )
        except Exception as e:
            raise e

    @pytest.mark.unit_test
    @pytest.mark.parametrize('user_type,entity_status', [
        (None, 'ANY'),
        ('normal_user', 'ANY'),
        ('owner_user', 'ANY'),
        ('moderator_user', 'ANY'),
    ])
    def test_publish_request_post(self, generate_entity_session, user_type, entity_status, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_entity_session['users'].get(user_type)
        else:
            user = AnonymousUser()
            user_type = 'Anonymous'

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        entity_id = entity.id
        entity_history_id = entity.history.first().history_id
        entity_kwargs = { 'pk': entity_id, 'history_id': entity_history_id }

        request = self.__build_http_request(
            user,
            url=live_server,
            method='POST',
            resolver_name='generic_entity_request_publish',
            resolver_kwargs=entity_kwargs
        )

        # validate response code
        expected_status_code = 302 if user_type == 'Anonymous' else 200

        response = RequestPublish.as_view()(request, **entity_kwargs)
        assert response.status_code == expected_status_code, \
               f'Status code mismatch, expected {expected_status_code} but got {response.status_code} for {user_type}'

        # validate content if applicable
        if response.status_code != 200:
            return

        expected_validity = user_type == 'owner_user'
        try:
            result = json.loads(response.content)

            form_validity = not not result.get('form_is_valid')
            assert form_validity == expected_validity, \
                'Mismatch on %s\'s PublishRequest, expected %s/%d to be a %s request but form was %s' % (
                    user_type, entity_id, entity_history_id,
                    'valid' if expected_validity else 'invalid',
                    'valid' if form_validity else 'invalid'
                )
        except Exception as e:
            raise e

    @pytest.mark.unit_test
    @pytest.mark.parametrize('user_type,entity_status', [
        (None, 'ANY'),
        ('normal_user', 'ANY'),
        ('owner_user', 'ANY'),
        ('moderator_user', 'ANY'),
    ])
    def test_publish_approve_get(self, generate_entity_session, user_type, entity_status, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_entity_session['users'].get(user_type)
        else:
            user = AnonymousUser()
            user_type = 'Anonymous'

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        entity_id = entity.id
        entity_history_id = entity.history.first().history_id
        entity_kwargs = { 'pk': entity_id, 'history_id': entity_history_id }

        request = self.__build_http_request(
            user,
            url=live_server,
            method='GET',
            resolver_name='generic_entity_publish',
            resolver_kwargs=entity_kwargs
        )

        # validate response code
        expected_status_code = 302 if user_type == 'Anonymous' else 200

        response = Publish.as_view()(request, **entity_kwargs)
        assert response.status_code == expected_status_code, \
               f'Status code mismatch, expected {expected_status_code} but got {response.status_code} for {user_type}'

        # validate content if applicable
        if response.status_code != 200:
            return

        try:
            result = json.loads(response.content)

            assert result.get('entity_type') == 'Phenotype', \
                'Mismatch on %s\'s PublishApproval, expected %s/%d to be \'Phenotype\' but got %s' % (
                    user_type, entity_id, entity_history_id, str(result.get('entity_type'))
                )

            assert result.get('entity_id') == entity_id, \
                'Mismatch on %s\'s PublishApproval, expected ID as %s but got %s' % (
                    user_type, entity_id, str(result.get('entity_id'))
                )

            assert result.get('entity_history_id') == entity_history_id, \
                'Mismatch on %s\'s PublishApproval, expected HistoryID as %d but got %s' % (
                    user_type, entity_history_id, str(result.get('entity_history_id'))
                )

            assert result.get('allowed_to_publish') == (user_type != 'normal_user'), \
                'Mismatch on %s\'s PublishApproval, expected to be able to publish %s/%d but got %s' % (
                    user_type, entity_id, entity_history_id, str(result.get('entity_type'))
                )
        except Exception as e:
            raise e

    @pytest.mark.unit_test
    @pytest.mark.parametrize('user_type,entity_status', [
        (None, 'ANY'),
        ('normal_user', 'ANY'),
        ('owner_user', 'ANY'),
        ('moderator_user', 'ANY'),
    ])
    def test_publish_approve_post(self, generate_entity_session, user_type, entity_status, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_entity_session['users'].get(user_type)
        else:
            user = AnonymousUser()
            user_type = 'Anonymous'

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        entity_id = entity.id
        entity_history_id = entity.history.first().history_id
        entity_kwargs = { 'pk': entity_id, 'history_id': entity_history_id }

        request = self.__build_http_request(
            user,
            url=live_server,
            method='GET',
            resolver_name='generic_entity_publish',
            resolver_kwargs=entity_kwargs
        )

        # validate response code
        expected_status_code = 302 if user_type == 'Anonymous' else 200

        response = Publish.as_view()(request, **entity_kwargs)
        assert response.status_code == expected_status_code, \
               f'Status code mismatch, expected {expected_status_code} but got {response.status_code} for {user_type}'

        # validate content if applicable
        if response.status_code != 200:
            return

        expected_validity = user_type == 'moderator_owner'
        try:
            result = json.loads(response.content)

            form_validity = not not result.get('form_is_valid')
            assert form_validity == expected_validity, \
                'Mismatch on %s\'s Publish approval, expected %s/%d to be a %s request but form was %s' % (
                    user_type, entity_id, entity_history_id,
                    'valid' if expected_validity else 'invalid',
                    'valid' if form_validity else 'invalid'
                )
        except Exception as e:
            raise e
