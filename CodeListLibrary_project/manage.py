#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    # decide which settings file to be used
    # cll.settings                        for normal app.
    # cll.test_settings                   for testing
    # cll.read_only_test_settings         for testing read-only

    if 'test' in sys.argv:
        # if a command contains read_only phrase at the end, then read cll.read_only_test_settings otherwise cll.test_settings
        if 'read_only' in sys.argv[-1]:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cll.read_only_test_settings")
            print("<<<<<<<   Running read-Only Tests   >>>>>>>")
        else:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cll.test_settings")
            print("<<<<<<<   Running Tests  >>>>>>>")

    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cll.settings")


    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError("Couldn't import Django. Are you sure it's installed and "
                              "available on your PYTHONPATH environment variable? Did you "
                              "forget to activate a virtual environment?")
        raise
    
    execute_from_command_line(sys.argv)
 