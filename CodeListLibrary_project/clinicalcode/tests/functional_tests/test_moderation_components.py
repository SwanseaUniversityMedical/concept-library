from django.urls import reverse
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import pytest

@pytest.mark.django_db
@pytest.mark.usefixtures('setup_webdriver')
class TestModerationComponents:
    COMPONENT_VISIBILITY_RULES = ['moderator_user', 'super_user']
    
    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type', [None, 'normal_user', 'moderator_user', 'super_user'])
    def test_moderation_redirect(self, login, logout, generate_user, user_type, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_user[user_type]
            login(self.driver, user.username, user.username + 'password')

        user_details = user_type if user else 'Anonymous'
        self.driver.get(live_server + reverse('moderation_page'))

        if user is not None and user_type not in self.COMPONENT_VISIBILITY_RULES:
            try:
                wait = WebDriverWait(self.driver, 5)
                wait.until(expected_conditions.title_contains('Permission Denied'))
            except Exception as e:
                if not isinstance(e, TimeoutException):
                    raise e
            finally:
                assert 'Phenotype Moderation' not in self.driver.title.lower(), \
                    f'Failed to present 403 status to {user_details} for Moderation page'
        else:
            expected_url = None
            if user is not None:
                expected_url = live_server + reverse('moderation_page')
            else:
                expected_url = '%s%s?next=%s' % (live_server, reverse('login'), reverse('moderation_page'))

            try:
                wait = WebDriverWait(self.driver, 5)
                wait.until(expected_conditions.url_to_be(expected_url))
            except Exception as e:
                if not isinstance(e, TimeoutException):
                    raise e
            finally:
                assert self.driver.current_url == expected_url, \
                    f'Failed to redirect via Moderation for {user_details} to {expected_url}'

        if user is not None:
           logout(self.driver)

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type', [None, 'normal_user', 'moderator_user', 'super_user'])
    def test_moderation_component_presence(self, login, logout, generate_user, user_type, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_user[user_type]
            login(self.driver, user.username, user.username + 'password')

        user_details = user_type if user else 'Anonymous'
        self.driver.get(live_server + reverse('search_phenotypes'))

        desired_visibility = user_type in self.COMPONENT_VISIBILITY_RULES
        component_presence = False
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, '''a.referral-card__title[href='%s']''' % reverse('moderation_page'))
            component_presence = elem is not None
        except Exception as e:
            if not isinstance(e, NoSuchElementException):
                raise e
            component_presence = False
        finally:
            assert component_presence == desired_visibility is not None, \
                   'Moderation component visiblility mismatch for %(user)s, expected %(desired)s but component was %(status)s' % {
                       'user': user_details,
                       'desired': 'visible' if desired_visibility else 'hidden',
                       'status': 'visible' if component_presence else 'hidden',
                   }

        if user is not None:
           logout(self.driver)
