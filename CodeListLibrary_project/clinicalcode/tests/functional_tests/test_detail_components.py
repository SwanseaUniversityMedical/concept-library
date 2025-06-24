
from django.urls import reverse
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import pytest

@pytest.mark.django_db
@pytest.mark.usefixtures('setup_webdriver')
class TestDetailComponents:

    @pytest.mark.functional_test
    def test_anonymous_publication_presence(self, live_server):
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : 'PH1' }))

        try:
            self.driver.find_element(By.ID, 'publication-information')
        except Exception as e:
            if not isinstance(e, NoSuchElementException):
                raise e
            present = False
        else:
            present = True
        finally:
            assert not present, 'Publication details are presented to anonymous user!'

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status', [
        ('moderator_user', 'REQUESTED'),
        ('owner_user', 'ANY')
    ])
    def test_publish_btn_presence(self, login, logout, generate_entity_session, user_type, entity_status, live_server):
        users = generate_entity_session['users']
        user = users.get(user_type)

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')
        print('Test Pub Ent:', entity, '|', entity.owner, '|', user)
        historical = entity.history.latest()

        login(self.driver, user.username, user.username + 'password')

        print(f'Test Pub: PH{entity.id}/V{historical.history_id}')
        self.driver.get(live_server + reverse('entity_history_detail', kwargs={ 'pk' : entity.id, 'history_id': historical.history_id }))

        present = False
        try:
            wait = WebDriverWait(self.driver, 5)
            wait.until(expected_conditions.presence_of_element_located((By.ID, 'publish-btn')))
        except Exception as e:
            if not isinstance(e, NoSuchElementException):
                raise e
            present = False
        else:
            present = True

        assert present, f'Publication button not visible for {user_type} when approval_status={entity_status}!'

        logout(self.driver)
