import time
from django.urls import reverse
import pytest
from selenium.webdriver.common.by import By


@pytest.mark.django_db
@pytest.mark.usefixtures("setup_webdriver")
class TestSearchFilters:

    @pytest.mark.parametrize('user_type', ['super_user'])
    def test_tags_filter(self, login, logout, generate_user, user_type, live_server):
        user = generate_user[user_type]
        # generate_entity.created_by = generate_user[user_type] this needed to test the page for at least some data

        login(self.driver, user.username, user.username + "password")

        self.driver.get(live_server + reverse('search_phenotypes'))

        accordian = self.driver.find_element(By.XPATH, "/html/body/main/div/div/aside/div[2]/div[4]")
        time.sleep(5)
        accordian.click()
        checkboxes = self.driver.find_elements(By.XPATH, "//input[(@class='checkbox-item') and (@aria-label = 'Tags')]")

        for checkbox in checkboxes:
            assert checkbox.is_enabled() is True

        logout(self.driver)
