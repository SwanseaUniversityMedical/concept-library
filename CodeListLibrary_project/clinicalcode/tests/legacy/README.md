
## CODE LIST LIBRARY TEST CODE

_26/10/2018, Pete Arnold_

The code is currently under development.

The test run procedure will run all tests in all directories within the
clinicalcode directory tree not just those in the test directory. Old tests may
be moved soon.


# The directory structure

Assuming the CodeListLibrary/CodeListLibrary_project directory is the base
directory. The tests have been gathered together at:

    clinicalcode/tests

This directory should contain any webdriver modules (e.g. chromedriver.exe). It
will also contain the base test classes and functions. The tests are gathered
in two folders - unit_tests and functional_tests.


# To run the tests :-

To run all of the tests, use:

    manage.py test

Note that this will not work if there is a tests.py file in the clinicalcode
directory as well as the tests directory.

