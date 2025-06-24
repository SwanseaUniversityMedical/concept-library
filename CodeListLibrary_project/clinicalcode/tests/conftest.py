import json
import socket
import time
import pytest

from datetime import datetime
from django.db import connection
from django.utils.timezone import make_aware
from django.contrib.auth.models import Group
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from django.contrib.auth import get_user_model

from clinicalcode.models import Brand
from clinicalcode.models import Concept
from clinicalcode.models import CodingSystem
from clinicalcode.models import GenericEntity
from clinicalcode.models import PublishedGenericEntity
from clinicalcode.models.Template import Template
from clinicalcode.models.EntityClass import EntityClass
from clinicalcode.entity_utils.constants import OWNER_PERMISSIONS, APPROVAL_STATUS, ENTITY_STATUS, WORLD_ACCESS_PERMISSIONS
from clinicalcode.tests.constants.constants import ENTITY_CLASS_FIELDS, TEMPLATE_DATA_V2, TEMPLATE_JSON_V1_PATH, TEMPLATE_FIELDS, \
    TEMPLATE_DATA, TEMPLATE_JSON_V2_PATH
from cll.test_settings import REMOTE_TEST_HOST, REMOTE_TEST, chrome_options


User = get_user_model()


@pytest.fixture
def generate_user(create_groups):
    """
    Pytest fixture for generating test users with different roles.

    This fixture creates several user instances with different roles for testing purposes. After the tests are finished,
    it deletes the created users to clean up the database.

    Returns:
        dict: A dictionary containing user instances with keys representing different roles.
            Keys:
                'super_user': Superuser instance
                'normal_user': Normal user instance
                'owner_user': Owner user instance
                'group_user': Group user instance
                'view_group_user': View group user instance
                'edit_group_user': Edit group user instance
    """
    su_user = User.objects.create_user(username='superuser', password='superuserpassword', email=None, is_superuser=True, is_staff=True)
    nm_user = User.objects.create_user(username='normaluser', password='normaluserpassword', email=None)
    ow_user = User.objects.create_user(username='owneruser', password='owneruserpassword', email=None)
    gp_user = User.objects.create_user(username='groupuser', password='groupuserpassword', email=None)
    md_user = User.objects.create_user(username='moderatoruser', password='moderatoruserpassword', email=None)
    vgp_user = User.objects.create_user(username='viewgroupuser', password='viewgroupuserpassword', email=None)
    egp_user = User.objects.create_user(username='editgroupuser', password='editgroupuserpassword', email=None)

    md_user.groups.add(create_groups['moderator_group'])

    users = {
            'super_user': su_user,
            'normal_user': nm_user,
            'owner_user': ow_user,
            'group_user': gp_user,
            'moderator_user': md_user,
            'view_group_user': vgp_user,
            'edit_group_user': egp_user,
    }

    for uobj in users.values():
        setattr(uobj, 'BRAND_OBJECT', {})
        setattr(uobj, 'CURRENT_BRAND', '')

    yield users

    # Clean up the users after the tests are finished
    for user in users.values():
        user.delete()


@pytest.fixture
def generate_entity_session(template, generate_user, brands=None):
    """
        Generate known entity data for publication tests through
        fixture composition

        Args:
            template (pytest.Fixture): reference to template fixture

            generate_user (pytest.Fixture): generate user(s) and group(s)

            brands (list|optional): optional list of brands to consider,
                                    defaults to 'None' which describes all
                                    brands

        Yields:
            A dict containing the generated users and entities
    """
    entities, ge_cleanup, cc_cleanup = {}, [], []
    if not isinstance(brands, list):
        brands = list(Brand.objects.all().values_list('id', flat=True))

    user = generate_user['owner_user']
    moderator = generate_user['moderator_user']

    system = CodingSystem.objects.create(
            name='Some system',
            link='',
            database_connection_name='',
            table_name='',
            code_column_name='',
            desc_column_name='',
    )

    concept = Concept.objects.create(
            name='Some concept',
            owner_id=user.id,
            entry_date=make_aware(datetime.now()),
            created_by=user,
            coding_system=system,
            owner_access=OWNER_PERMISSIONS.EDIT,
    )
    cc_cleanup.append(concept.id)

    template_data = {
            'concept_information': [
                    {'concept_id': concept.id, 'concept_version_id': concept.history.first().history_id}
            ]
    }

    for status in APPROVAL_STATUS:
        entity = GenericEntity.objects.create(
                name='TEST_%s_Entity' % status.name,
                author=user.username,
                status=ENTITY_STATUS.DRAFT.value,
                publish_status=status.value,
                template=template,
                template_version=1,
                template_data=template_data,
                created_by=user,
                world_access=WORLD_ACCESS_PERMISSIONS.VIEW
        )

        record = {'entity': entity}
        ge_cleanup.append(entity.id)

        if status != APPROVAL_STATUS.ANY:
            metadata = {}
            if status != APPROVAL_STATUS.PENDING:
                metadata.update({'moderator_id': moderator.id})

            record.update({
                    'published_entity': PublishedGenericEntity.objects.create(
                            **metadata,
                            entity=entity,
                            entity_history_id=entity.history.first().history_id,
                            modified=make_aware(datetime.now()),
                            approval_status=status.value,
                            created_by_id=user.id
                    )
            })

        entities[status.name] = record

    yield {
            'entities': entities,
            'users': generate_user
    }

    with connection.cursor() as cursor:
        cursor.execute('''
        -- rm entities
        delete from public.clinicalcode_genericentity
         where id = any(%(entity_ids)s);

        delete from public.clinicalcode_historicalgenericentity
         where id = any(%(entity_ids)s);

        delete from public.clinicalcode_publishedgenericentity
         where entity_id = any(%(entity_ids)s);

        delete from public.clinicalcode_historicalpublishedgenericentity
         where entity_id = any(%(entity_ids)s);

        -- rm concepts
        delete from public.clinicalcode_concept
         where id = any(%(concept_ids)s);

        delete from public.clinicalcode_historicalconcept
         where id = any(%(concept_ids)s);

        delete from public.clinicalcode_publishedconcept
         where concept_id = any(%(concept_ids)s);

        delete from public.clinicalcode_historicalpublishedconcept
         where concept_id = any(%(concept_ids)s);

        -- rm coding system
        delete from public.clinicalcode_codingsystem
         where name = 'Some system';

        delete from public.clinicalcode_historicalcodingsystem
         where name = 'Some system';
        ''', params={'entity_ids': ge_cleanup, 'concept_ids': cc_cleanup})


@pytest.fixture
def create_groups():
    """
    Pytest fixture for creating test groups.

    This fixture creates several group instances for testing purposes. After the tests are finished,
    it deletes the created groups to clean up the database.

    Returns:
        dict: A dictionary containing group instances with keys representing different groups.
            Keys:
                'permitted_group': Permitted group instance
                'forbidden_group': Forbidden group instance
                'view_group': View group instance
                'edit_group': Edit group instance
    """
    moderator_group, created_moderator = Group.objects.get_or_create(name="Moderators")
    permitted_group = Group.objects.create(name="permitted_group")
    forbidden_group = Group.objects.create(name="forbidden_group")
    view_group = Group.objects.create(name="view_group")
    edit_group = Group.objects.create(name="edit_group")

    # Yield the created groups, so they can be used in tests
    yield {
            'moderator_group': moderator_group,
            'permitted_group': permitted_group,
            'forbidden_group': forbidden_group,
            'view_group': view_group,
            'edit_group': edit_group,
    }

    # Clean up the groups after the tests are finished
    for group in [permitted_group, forbidden_group, view_group, edit_group]:
        group.delete()

    if created_moderator:
        moderator_group.delete()


@pytest.fixture
def entity_class():
    """
    Pytest fixture for creating a test instance of the EntityClass model.

    This fixture creates a single instance of the EntityClass model with predefined fields for testing purposes.

    Returns:
        EntityClass: An instance of the EntityClass model with predefined fields.
    """
    entity_class = EntityClass.objects.create(**ENTITY_CLASS_FIELDS)

    yield entity_class


@pytest.fixture
def template(entity_class):
    """
    Pytest fixture for creating a test instance of the Template model.

    This fixture creates a single instance of the Template model with predefined fields and a template JSON file
    for testing purposes.

    Args:
        entity_class (EntityClass): An instance of the EntityClass model associated with the template.

    Returns:
        Template: An instance of the Template model with predefined fields and a template JSON.
    """
    with open(TEMPLATE_JSON_V1_PATH) as f:
        template_json = json.load(f)

    template = Template.objects.create(**TEMPLATE_FIELDS,
                                       definition=template_json,
                                       entity_class=entity_class,
                                       )
    yield template
    
    # Teardown code
    Template.objects.all().delete()  # Delete all template instances


@pytest.fixture
def generate_entity(create_groups, template):
    """
    Pytest fixture for creating a test instance of the GenericEntity model.

    Args:
        create_groups (dict): A dictionary containing group instances.
        template (Template): An instance of the Template model associated with the entity.

    Returns:
        GenericEntity: An instance of the GenericEntity model with predefined fields.
    """
    generate_entity = GenericEntity(name="Test entity",
                                    author="Tester author",
                                    group=create_groups['permitted_group'],
                                    template_data=TEMPLATE_DATA, updated=make_aware(datetime.now()),
                                    template=template, template_version=template.template_version,definition = 'Phenotype definition')
    yield generate_entity

    GenericEntity.objects.all().delete()



@pytest.fixture(scope="class")
def setup_webdriver(request):
    """
    Pytest fixture for setting up a WebDriver instance for class-scoped tests.

    Args:
        request: Pytest request object.

    Yields:
        None
    """
    if REMOTE_TEST:
        driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Remote(command_executor=REMOTE_TEST_HOST, options=chrome_options)
    wait = WebDriverWait(driver, 10)
    driver.maximize_window()
    request.cls.driver = driver
    request.cls.wait = wait
    yield
    driver.quit()


def pytest_configure(config):
    """
    Pytest configuration hook to set the liveserver based on the remote test flag.

    Args:
        config: Pytest config object.

    Returns:
        None
    """
    if REMOTE_TEST:
        config.option.liveserver = "localhost:8080"
    else:
        config.option.liveserver = socket.gethostbyname(socket.gethostname())


@pytest.fixture(scope="function")
def login(live_server):
    """
    Pytest fixture for performing login during tests.

    Args:
        live_server: Pytest fixture providing the live server URL.

    Yields:
        Callable: A function for performing login.
    """

    def _login(driver, username, password):
        print(f"Live server URL: {live_server.url}")
        driver.get(live_server.url + "/account/login/")
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        # Input username and password
        username_input.send_keys(username)
        password_input.send_keys(password)

        # Submit the form by pressing Enter
        password_input.send_keys(Keys.ENTER)

    yield _login



@pytest.fixture(scope="function")
def logout(live_server):
    """
    Pytest fixture for performing logout during tests.

    Args:
        live_server: Pytest fixture providing the live server URL.

    Yields:
        Callable: A function for performing logout.
    """

    def _logout(driver):
        driver.get(live_server.url + "/account/logout/")

    yield _logout

@pytest.fixture
def template_v2(template):
    """
    Pytest fixture for creating a Template instance with version 2.

    Args:
        template (Template): An existing template instance.
        new_template_definition (dict): The new template definition.

    Returns:
        Template: An instance of the Template model with version 2.
    """
    with open(TEMPLATE_JSON_V2_PATH) as f:
        new_template = json.load(f)

    template.definition = new_template
    template.template_version = 2
    template.save()
    yield template
    # Teardown code
    Template.objects.all().delete()  # Delete all template instances


@pytest.fixture
def generic_entity_v2(create_groups, template_v2):
    """
    Pytest fixture for creating a GenericEntity instance with version 2.

    Args:
        create_groups (dict): A dictionary containing group instances.
        template_v2 (Template): An instance of the Template model with version 2.

    Returns:
        GenericEntity: An instance of the GenericEntity model with template version 2.
    """
    generate_entity = GenericEntity(name="Test entity",
                                    author="Tester author",
                                    group=create_groups['permitted_group'],
                                    
                                    template_data=TEMPLATE_DATA_V2, updated=make_aware(datetime.now()),
                                    template=template_v2, template_version=template_v2.template_version,
                                    definition = 'Phenotype definition')
    
    yield generate_entity
    GenericEntity.objects.all().delete()

@pytest.fixture(autouse=True)
def use_debug(settings):
    """
    Pytest fixture for setting the DEBUG flag to True during tests.

    Args:
        settings: Django settings fixture.

    Yields:
        None
    """
    settings.DEBUG = True
    yield
