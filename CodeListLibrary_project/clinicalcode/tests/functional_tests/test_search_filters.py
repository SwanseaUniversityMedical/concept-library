from django.urls import reverse
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import time
import pytest

@pytest.mark.django_db(reset_sequences=True,transaction=True)
@pytest.mark.usefixtures("setup_webdriver")
class TestSearchFilters:

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_tags_filter(self, login, logout, generate_user, user_type, live_server):
        user = None
        if isinstance(user_type, str):
            user = generate_user[user_type]
            login(self.driver, user.username, user.username + 'password')
        # generate_entity.created_by = generate_user[user_type] this needed to test the page for at least some data

        self.driver.get(live_server + reverse('search_entities'))

        uname = self.driver.find_element(By.CLASS_NAME, 'text-username').text if user is not None else user_type
        print(f"Current username: {uname}")

        try:
            wait = WebDriverWait(self.driver, 5)
            accordion = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.accordion[data-field="tags"] label')))
            accordion.click()

            time.sleep(1)

            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, 'input[data-field="tags"]')
            for checkbox in checkboxes:
                assert checkbox.is_enabled() is True

        except Exception as e:
            if not isinstance(e, TimeoutException):
                raise e

        if user is not None:
           logout(self.driver)
