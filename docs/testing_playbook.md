# Pytest Module - Ways of Working

Roshan Toby, Artur Zinnurov  
*Document last updated on 20/10/2024*
---

## Purpose

This document outlines guidelines and best practices for working with the Pytest module in our project. These guidelines are designed to ensure consistency, maintainability, and efficiency in our testing processes.


## Table of Contents
1. [Setting Up Pytest](#setting-up-pytest)
2. [Test Organization](#test-organization)
3. [Writing Tests](#writing-tests)
4. [Running Tests](#running-tests)
5. [Test Fixtures](#test-fixtures)
6. [Mocking](#mocking)
7. [Documentation](#documentation)
8. [Continuous Integration](#continuous-integration)
9. [Resources](#resources)


## 1. Setting Up Pytest

Before you start using Pytest for your project, make sure to install it using your preferred package manager. 

We recommend using `pip` in your virtual environment:

```bash
pip install pytest
```

All test requirements are present in `docker/requirements/test.txt`


## 2. Test Organization

In our project, we follow a structured approach to organizing tests, ensuring clarity and consistency across different 
types of tests.

### Test Naming Convention

All test files should start with the prefix `test_`. This convention helps to easily identify test files in the project 
directory.

```
├───CodeListLibrary_project
│   ├───clinicalcode
│   │   ├───tests
│   │   │   ├───allure-reports
│   │   │   ├───allure-results
│   │   │   ├───constants
│   │   │   │   └───constants.py
│   │   │   ├───functional_tests
│   │   │   │   └───test_functional_module1.py
│   │   │   ├───legacy
│   │   │   ├───unit_tests
│   │   │   │   └───test_unit_module1.py
│   ├───cll
├───docker
└───docs
```

### Unit Tests

Unit tests, which focus on testing individual components or functions, are stored in the `unit_tests` folder.

### Functional Tests

Functional tests, which assess the behavior of a system as a whole, are stored in the `functional_tests` folder.

### Test Constants

All constant files containing test data are stored in the `CodeListLibrary_project/clinicalcode/tests/constants` folder and common python constants used across different tests are centralized in the `CodeListLibrary_project/clinicalcode/tests/constants/constants.py` file.

This organizational structure enhances maintainability and readability while ensuring that test-related resources are neatly categorized.


## 3. Writing Tests

Writing effective tests is crucial for maintaining a reliable codebase. Follow these best practices to ensure clarity, maintainability, and effectiveness in your test suite.

### Purpose of Tests

Clearly document the purpose of each test. A descriptive test name goes a long way in understanding the intended behavior being tested. For example:

```python
# test_unit_module1.py
def test_addition():
    """Test the addition function."""
    result = addition(2, 3)
    assert result == 5
```   
### AAA Pattern

Follow the Arrange-Act-Assert (AAA) pattern when structuring your tests. This pattern helps maintain clarity in your test logic:

```python
# test_unit_module2.py
def test_multiply():
    """Test the multiply function."""
    # Arrange
    a, b = 2, 3

    # Act
    result = multiply(a, b)

    # Assert
    assert result == 6
```

### Descriptive Naming
Use descriptive names for your test functions and variables. This makes it easier to understand the purpose of the test.

### Writing tests in a class
When writing tests using Pytest, you can utilize the class-based test structure provided by Pytest.

Here's an example demonstrating how to write tests within a class:

``` python
# my_module.py

def add_numbers(a, b):
    return a + b

def multiply_numbers(a, b):
    return a * b
```
Now, let's write tests for the functions in the my_module.py module using a class-based approach:
``` python
# test_my_module.py
from my_module import add_numbers, multiply_numbers

import pytest

class TestMyModule:
    def test_add_numbers(self):
        result = add_numbers(2, 3)
        assert result == 5

    def test_multiply_numbers(self):
        result = multiply_numbers(2, 3)
        assert result == 6

    # Add more test methods as needed
    # ...

``` 
Remember that each test method should be independent, and you can use fixtures within the class if there's common setup 
or cleanup needed for multiple tests.

### Purpose of conftest.py
The conftest.py file is used to share fixtures, configuration, and custom hooks across multiple test files. It is automatically discovered by Pytest and can be placed at different levels of your project directory to 
target specific scopes.

Fixtures are a powerful feature in Pytest for setting up preconditions and sharing resources among tests. They allow you to provide a consistent and controlled environment for your tests. By leveraging conftest.py, you can avoid duplication of setup code and create a consistent environment for your tests.

Example conftest.py:

```
tests/
    __init__.py

    conftest.py
        # content of tests/conftest.py
        import pytest

        @pytest.fixture
        def order():
            return []

        @pytest.fixture
        def top(order, innermost):
            order.append("top")

    test_top.py
        # content of tests/test_top.py
        import pytest

        @pytest.fixture
        def innermost(order):
            order.append("innermost top")

        def test_order(order, top):
            assert order == ["innermost top", "top"]
```


## 4. Test Fixtures

Fixtures are a powerful feature in Pytest that allows you to set up and provide a consistent environment for your tests. This guide will walk you through the basics of fixtures, how to create them, and best practices for using them effectively in your test suite.

A fixture is a function marked with the `@pytest.fixture` decorator that can be used to set up preconditions for your tests. Fixtures are a way to modularize and share setup code across multiple tests.

### Creating a Fixture

To create a fixture, define a function and use the `@pytest.fixture` decorator:

```python
# conftest.py or test_module.py
import pytest

@pytest.fixture
def my_fixture():
    """A simple fixture."""
    setup_code = "Setup steps go here"
    yield setup_code  # This is the value that will be provided to the test
    # Teardown code (optional) can go here
```

### Using Fixtures in Tests
Tests can use fixtures by including the fixture function as an argument:

```python
# test_module.py
def test_example(my_fixture):
    """Test using the 'my_fixture' fixture."""
    assert my_fixture == "Setup steps go here"
```

### Scope of Fixtures
Fixtures can have different scopes to control when they are set up and torn down.

The default scope is function, meaning the fixture is set up and torn down for each test function. Other scopes include module, class, and session. 

Higher-scoped fixtures are executed first, within a function request for fixtures, those of higher-scopes (such as session) are executed before lower-scoped fixtures (such as function or class).

### Fixture Dependencies
Fixtures can depend on other fixtures. When a test requests a fixture, Pytest ensures that all its dependencies are set up first: 

```python
# conftest.py or test_module.py
import pytest

@pytest.fixture
def base_fixture():
    """Base fixture."""
    setup_code = "Base setup steps go here"
    yield setup_code

@pytest.fixture
def dependent_fixture(base_fixture):
    """Fixture dependent on 'base_fixture'."""
    setup_code = base_fixture + " and additional setup steps"
    yield setup_code
```

### Fixture Finalization and Teardown
You can perform cleanup or teardown steps after the test is completed using the yield statement in a fixture:

```python
# conftest.py or test_module.py
import pytest

@pytest.fixture
def setup_and_teardown_fixture():
    """Fixture with setup and teardown steps."""
    setup_code = "Setup steps go here"
    yield setup_code
    # Teardown code (optional) can go here
    print("Teardown steps go here")
```

For more advanced usage and additional options, refer to the [Pytest Fixture Documentation](https://docs.pytest.org/en/7.1.x/reference/fixtures.html#).

### Handling Sequence Resets
When using pytest for testing a Django application, you may encounter issues where database sequences (such as those used for primary keys in PostgreSQL) do not reset between test runs. This can cause tests that rely on specific sequence values to fail.

To ensure that database sequences are reset between tests, you can use the @pytest.mark.django_db decorator with the reset_sequences and transaction parameters. This forces pytest to reset sequences and use a transaction for each test, ensuring a clean state.

- `reset_sequences=True`: Resets database sequences between tests.
- `transaction=True`: Wraps the test in a database transaction, which can be useful to ensure that the database state is rolled back completely after the test runs.

```python
import pytest
from myapp.models import MyModel

@pytest.mark.django_db(reset_sequences=True, transaction=True)
class TestMyModel:
    def test_instance_creation(self):
        instance = MyModel.objects.create(name="Test")
        assert instance.id == 1  # Assuming this test relies on the primary key starting from 1

    def test_another_instance_creation(self):
        instance = MyModel.objects.create(name="Another Test")
        assert instance.id == 1  # Each test method will have sequences reset
```


## 5. Running Tests

Instructions on how to run tests locally:

1. Put your dev git.token file to the docker/development/db/git.token

2. Run ```docker compose -p cll -f docker-compose.dev.yaml --profile test up --build```

3. Make sure that in PGadmin you will see the clluser_test user

4. Exec into the container, e.g. `docker exec -it cll-web-test-1 /bin/bash` (use `docker ps -a` to get the container name as it may differ from `cll-web-test-1`)

5. Inside of the web-test container type ```pytest -s -v``` or ```pytest ``` if you do not want to see print statement

6. For functional test using selenium you can view local sessions at http://localhost:4444/.

7. If you encounter any problems run ```docker compose -p cll -f docker-compose.dev.yaml --profile test down --volumes```


## 6. Mocking

Best practices for using mocks, including the recommendation to use `pytest-mock` and a reminder not to overuse mocks.


## 7. Documentation

Well-documented test code is essential for ensuring that team members can understand, maintain, and extend the test suite effectively. Follow these guidelines to ensure thorough documentation in your Pytest module.

- Use descriptive and clear names for your test functions. A well-chosen test name should convey the purpose of the test without needing to delve into the test code.
- Include docstrings for each test function. A docstring should provide a brief description of the test's purpose, the input values, and the expected outcomes.
- Document common usage scenarios for fixtures, configuration settings, and any testing conventions specific to your project. Explain when and why this fixture is used, and include usage scenarios.
- Document constants stored in `CodeListLibrary_project/clinicalcode/tests/constants/constants.py`. Maintain a dedicated file for constants and provide descriptions for each constant.


## 8. Continuous Integration

Our Continuous Integration (CI) pipeline triggers with every Pull Request (PR) into the master branch, running Pytest tests and providing code coverage insights directly in the PR. Additionally, Allure reports are generated to showcase detailed test results and statistics. These reports are published on GitHub Pages, ensuring quick access to essential information during the review process. Concept Library has integrated pipline for the tests but it is advisable to not change the `docker/env/remote.test.env` file.

After succesfull run of CI you can go to this URL to check test results remotely - https://meek-florentine-a03d43.netlify.app/ 


## 9. Resources

 - [Pytest Documentation](https://docs.pytest.org/en/7.1.x/how-to/index.html)
 - Tutorials
    - [Real Python - Getting Started with Pytest](https://realpython.com/pytest-python-testing/)
    - [Pytest Tutorial – How to Test Python Code](https://www.youtube.com/watch?v=cHYq1MRoyI0)
 - Book
    - [Python Testing with pytest](https://www.amazon.co.uk/Python-Testing-pytest-Brian-Okken/dp/1680502409)
 - GitHub Repositories
    - [pytest](https://github.com/pytest-dev/pytest)
    - [A curated list of awesome pytest resources](https://github.com/augustogoulart/awesome-pytest)

Happy Testing :)

