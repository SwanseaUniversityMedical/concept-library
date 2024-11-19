
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

    users_params = [
        ('owner_user', 'ANY'), ('owner_user', 'APPROVED'),('owner_user', 'REQUESTED'),
    ]

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',users_params)
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
    
    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',users_params)
    def test_ws_button_no_concepts(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        delete_icon = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "delete-icon")))
        delete_icon.click()

        confirm_button_modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
        confirm_button_modal.click()


        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))

        assert attribute_button.is_enabled() == False
        logout(self.driver)

        """alert = WebDriverWait(self.driver, 10).until(lambda d : d.switch_to.alert)
            alert.accept()"""

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',users_params)
    @pytest.mark.skip(reason="Need to fix position of page")
    def test_ws_button_added_concepts(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        delete_icon = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "delete-icon")))
        delete_icon.click()

        confirm_button_modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
        confirm_button_modal.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))

        assert attribute_button.is_enabled() == False

        create_concept_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "create-concept-btn")))
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", create_concept_button)
        create_concept_button.click()

     
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//select[@id='coding-system-select']/option[text()='Some system']"))).click()

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-changes"))).click()

        assert attribute_button.is_enabled() == True

        logout(self.driver)
        """alert = WebDriverWait(self.driver, 10).until(lambda d : d.switch_to.alert)
            alert.accept()"""
 
    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',users_params)
    def test_ws_attributerow_exist(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))
        attribute_button.click()

        
        time.sleep(5)
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "SELECTION"))).click()

        attribute_row = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "fill-accordian__label")))

        assert attribute_row.is_enabled() == True
        time.sleep(5)

        logout(self.driver)

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',users_params)
    def test_ws_attributerow_settings(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))
        attribute_button.click()

        
        time.sleep(5)
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "SELECTION"))).click()

        attribute_row = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "fill-accordian__label")))
        attribute_row.click()

        input_attribute_name = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[starts-with(@id, 'attribute-name-input-')]")))
        input_attribute_name.clear()
        input_attribute_name.send_keys('Selenium test')


        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//select[@class='selection-input']/option[text()='STRING']"))).click()

        time.sleep(5)

        confirm_attribute_changes = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[starts-with(@id, 'confirm-changes-')]")))
        confirm_attribute_changes.click()

        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "ATTRIBUTE_TABLE"))).click()

        time.sleep(5)

        tab_content = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "tab-content")))
        assert "Selenium test" in tab_content.text
    
        logout(self.driver)

    @pytest.mark.functional_test
    @pytest.mark.parametrize('user_type,entity_status',users_params)
    def test_ws_delete_row(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))
        attribute_button.click()

        
        time.sleep(5)
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "SELECTION"))).click()
        
        delete_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "fill-accordian__label__delete-icon")))
        delete_button.click()

        box_attribute = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "no-items-selected")))
        assert "You haven't selected any attributes yet" in box_attribute.text
        logout(self.driver)


    @pytest.mark.functional_test       
    @pytest.mark.parametrize('user_type,entity_status,attribute_type', [
        ('owner_user', 'ANY', 'STRING'), 
        ('owner_user', 'APPROVED', 'INT'),
        ('owner_user', 'REQUESTED', 'FLOAT'),
    ]) 
    def test_ws_value_type(self, live_server, generate_entity_session, user_type, attribute_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))
        attribute_button.click()

        
        time.sleep(5)
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "SELECTION"))).click()

        attribute_row = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "fill-accordian__label")))
        attribute_row.click()

        input_attribute_name = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[starts-with(@id, 'attribute-name-input-')]")))
        input_attribute_name.clear()
        input_attribute_name.send_keys('Selenium test')


        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, f"//select[@class='selection-input']/option[text()='{attribute_type}']"))).click()

        time.sleep(5)

        confirm_attribute_changes = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[starts-with(@id, 'confirm-changes-')]")))
        confirm_attribute_changes.click()

        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "ATTRIBUTE_TABLE"))).click()

        time.sleep(5)

        
        row_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//td[@class='gridjs-td' and @contenteditable='true']"))
        )
        row_element.clear()
        if (attribute_type == "STRING"):
            row_element.send_keys('%3')
            
            confirm_button_modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
            confirm_button_modal.click()

            assert "Attribute Selenium test with row index 1 is not a string" in self.driver.page_source

        elif (attribute_type == "INT"):
            row_element.send_keys("test")
              
            confirm_button_modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
            confirm_button_modal.click()
            
            time.sleep(3)
            
            assert "Attribute Selenium test with row index 1 is not an integer" in self.driver.page_source
        elif (attribute_type == "FLOAT"):
            row_element.send_keys("test")
              
            confirm_button_modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
            confirm_button_modal.click()
            
            time.sleep(3)
            
            
            assert "Attribute Selenium test with row index 1 is not a float" in self.driver.page_source
    
        logout(self.driver)

    
    @pytest.mark.functional_test       
    @pytest.mark.parametrize('user_type,entity_status', users_params)
    def test_ws_detail_page(self, live_server, generate_entity_session, user_type, generate_user, login, entity_status, logout):
        user = generate_user[user_type]
        login(self.driver, user.username, user.username + "password")

        entities = generate_entity_session['entities']
        record = entities.get(entity_status)
        entity = record.get('entity')

        
        self.driver.get(live_server + reverse('entity_detail_shortcut', kwargs={ 'pk' : entity.id }))

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='topButtons']/div/div/button[1]")))
        edit_button = self.driver.find_element(By.XPATH, "//*[@id='topButtons']/div/div/button[1]")
        edit_button.click()

        attribute_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "add-concept-attribute-btn")))
        attribute_button.click()


        
        row_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//td[@class='gridjs-td' and @contenteditable='true']"))
        )
        row_element.clear()

        row_element.send_keys('1')
            
        confirm_button_modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
        confirm_button_modal.click()

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "submit-entity-btn"))).click()
        
        time.sleep(5)

        concept_list = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "fill-accordian__label")))
        concept_list.click()

        assert "CONCEPT ATTRIBUTE - Attribute test name - INT - 1" in self.driver.page_source

        logout(self.driver)
                




 
