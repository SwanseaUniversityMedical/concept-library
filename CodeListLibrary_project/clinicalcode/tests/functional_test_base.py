'''
    Test base class

    Set-up and tear-down etc. for unit tests and functional tests.
'''
import os
import time
import datetime
#from django.conf import settings
from cll import test_settings as settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from clinicalcode.tests.test_base import *

SCREEN_DUMP_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'screendumps'
)

base_url = settings.WEBAPP_HOST
login_url = base_url + '/account/login?next=/'

'''
    Test helper functions.
'''
MAX_WAIT = 10
def wait(fn):
    def modified_fn(*args, **kwargs):
        start_time = time.time()
        while True:
            try:
                return fn(*args, **kwargs)
            except (AssertionError, WebDriverException) as e:
                if time.time() - start_time > MAX_WAIT:
                    raise e
                time.sleep(0.5)
    return modified_fn


class FunctionalTest(StaticLiveServerTestCase):

    def setUp(self):      
        if settings.REMOTE_TEST:
            self.browser = webdriver.Remote(command_executor=settings.REMOTE_TEST_HOST,
                                            desired_capabilities=settings.chrome_options.to_capabilities())
            self.browser.implicitly_wait(settings.IMPLICTLY_WAIT)
        else:
            self.browser = webdriver.Chrome()

    def list2reason(self, exc_list):
        if exc_list and exc_list[-1][0] is self:
            return exc_list[-1][1]
        
    def tearDown(self):
        print("Functional test tear-down ...")
        self.result = getattr(self, '_outcomeForDoCleanups', self._resultForDoCleanups)
        #error = self.list2reason(result.errors)
        #failure = self.list2reason(result.failures)
        #ok = not error and not failure
        if self._test_has_failed():
            if not os.path.exists(SCREEN_DUMP_LOCATION):
                os.makedirs(SCREEN_DUMP_LOCATION)
            for ix, handle in enumerate(self.browser.window_handles):
                self._windowid = ix
                self.browser.switch_to_window(handle)
                self.take_screenshot()
                self.dump_html()
        self.browser.quit()
        #super(StaticLiveServerTestCase).tearDown()

    def _test_has_failed(self):
        # slightly obscure but couldn't find a better way!
        return any(error for (method, error) in self.result.errors)

    def take_screenshot(self):
        filename = self._get_filename() + '.png'
        print(('sending screenshot to', filename))
        self.browser.get_screenshot_as_file(filename)

    def dump_html(self):
        filename = self._get_filename() + '.html'
        print(('dumping page HTML to', filename))
        with open(filename, 'w') as f:
            f.write(self.browser.page_source.encode('utf8'))

    def _get_filename(self):
        timestamp = datetime.datetime.now().isoformat().replace(':', '.')[:19]
        return '{folder}/{classname}.{method}-window{windowid}-{timestamp}'.format(
            folder=SCREEN_DUMP_LOCATION,
            classname=self.__class__.__name__,
            method=self._testMethodName,
            windowid=self._windowid,
            timestamp=timestamp
        )
