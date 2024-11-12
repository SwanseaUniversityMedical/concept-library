import time
from django.urls import reverse
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytest

@pytest.mark.django_db(reset_sequences=True, transaction=True)
@pytest.mark.usefixtures('setup_webdriver')
class TestWorkingsetComponents:

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',[
        ('owner_user', 'ANY'), ('owner_user', 'APPROVED'),('owner_user', 'REQUESTED'),
    ])
    def test_ws_button_presence(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        # generate_entity.created_by = generate_user[user_type] this needed to test the page for at least some data

        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))
        assert attribute_button
        logout(self.driver)