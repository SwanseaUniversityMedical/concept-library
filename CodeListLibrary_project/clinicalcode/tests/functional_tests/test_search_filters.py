import time
from django.urls import reverse
import pytest
from selenium.webdriver.common.by import By


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

        accordion = self.driver.find_element(By.XPATH, "/html/body/main/div/div/aside/div[2]/div[4]")
        time.sleep(5)
        accordion.click()
        checkboxes = self.driver.find_elements(By.XPATH, "//input[(@class='checkbox-item') and (@aria-label = 'Tags')]")

        for checkbox in checkboxes:
            assert checkbox.is_enabled() is True

        if user is not None:
           logout(self.driver)
