from django.urls import reverse
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import pytest

@pytest.mark.django_db
@pytest.mark.usefixtures('setup_webdriver')
class TestCollectionComponents:

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type', [None, 'normal_user'])
    def test_collection_redirects(self, login, logout, generate_user, user_type, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_user[user_type]
            login(self.driver, user.username, user.username + 'password')

        user_details = user_type if user else 'Anonymous'
        self.driver.get(live_server + reverse('search_phenotypes'))

        element = None
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, '''a.referral-card__title[href='%s']''' % reverse('my_collection'))
        except Exception as e:
            if not isinstance(e, NoSuchElementException):
                raise e
        finally:
            assert element is not None, f'My Collection component not visible for {user_details}!'

        if user:
            expected_url = live_server + reverse('my_collection')
        else:
            expected_url = '%s%s?next=%s' % (live_server, reverse('login'), reverse('my_collection'))

        try:
            element.click()

            wait = WebDriverWait(self.driver, 5)
            wait.until(expected_conditions.url_to_be(expected_url))
        except Exception as e:
            if not isinstance(e, TimeoutException):
                raise e
        finally:
            assert self.driver.current_url == expected_url, \
                   f'Failed to redirect via My Collections for {user_details} to {expected_url}'

        if user is not None:
           logout(self.driver)
