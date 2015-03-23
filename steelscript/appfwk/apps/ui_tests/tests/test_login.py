import os
from contextlib import contextmanager

from steelscript.appfwk.apps.devices.models import Device
from steelscript.appfwk.apps.preferences.models import AppfwkUser

import tzlocal
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import management
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


REQUIRED_SETTINGS = ('TEST_DEVICES', 'TEST_USER_TIMEZONE')

for value in REQUIRED_SETTINGS:
    if not hasattr(settings, value):
        raise AttributeError("Missing 'settings.%s'.\n"
                             'Please see apps/ui_tests/README.rst for '
                             'required settings for these UI selenium tests.' %
                             value)


@contextmanager
def local_timezone():
    """Temporarily set environment TZ to local timezone."""
    local_tz = tzlocal.get_localzone().zone
    current_tz = os.getenv('TZ', local_tz)
    os.environ['TZ'] = local_tz
    yield
    os.environ['TZ'] = current_tz


class BaseSeleniumTests(StaticLiveServerTestCase):
    """Base class for selenium based tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseSeleniumTests, cls).setUpClass()
        # load a single report
        management.call_command(
            'reload',
            report_name='steelscript.appfwk.reports.overall'
        )
        try:
            cls.user = AppfwkUser.objects.get(username='admin')
        except ObjectDoesNotExist:
            cls.user = AppfwkUser.objects.create_superuser(
                'admin', 'admin@admin.com', 'admin')

        with local_timezone():
            cls.driver = WebDriver()
            cls.driver.implicitly_wait(3)

    @classmethod
    def tearDownClass(cls):
        super(BaseSeleniumTests, cls).tearDownClass()
        cls.driver.quit()

    def login(self):
        """Login to new instance of server."""
        # get login page as a new user
        self.driver.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.driver.find_element_by_name("username")
        self.assertEqual(username_input.get_attribute('placeholder'),
                         'type your username')
        username_input.send_keys('admin')
        password_input = self.driver.find_element_by_name("password")
        self.assertEqual(password_input.get_attribute('placeholder'),
                         'type your password')
        password_input.send_keys('admin')
        submit = self.driver.find_element_by_id('submit')
        submit.click()


class NewUserSetupTests(BaseSeleniumTests):
    """Test the sequence of events when a new user logs into the system."""

    def test_login_sequence(self):
        self.login()

        # new users are presented with their preferences to update
        # wait for page load
        WebDriverWait(self.driver, 5).until(EC.title_contains('User Pref'))
        self.assertTrue('preferences' in self.driver.current_url)

        # update fields
        email_input = self.driver.find_element_by_id('id_email')
        email_input.clear()
        email_input.send_keys('admin@test.com')

        timezone = Select(self.driver.find_element_by_id('id_timezone'))
        timezone.select_by_visible_text(settings.TEST_USER_TIMEZONE)

        update = self.driver.find_element_by_xpath('//input[@value="Update"]')
        update.click()

        # next new users will see the devices page
        # wait for page load
        WebDriverWait(self.driver, 5).until(EC.title_contains('Devices'))
        self.assertTrue('/devices/' in self.driver.current_url)

        # verify we have no devices defined yet
        table = self.driver.find_element_by_xpath('//form/table/tbody/tr/td')
        self.assertEqual(table.text, 'No devices defined yet.')

        # add new devices as stored in settings - test setup only
        for device in settings.TEST_DEVICES:
            addbtn = self.driver.find_element_by_link_text('Add New Device')
            addbtn.click()

            WebDriverWait(self.driver, 5).until(EC.title_contains('Detail'))
            self.assertTrue('/devices/add/' in self.driver.current_url)

            self.driver.find_element_by_id('id_name').send_keys(device['name'])

            module = Select(self.driver.find_element_by_id('id_module'))
            module.select_by_visible_text(device['module'])

            self.driver.find_element_by_id('id_host').send_keys(device['host'])

            # port field is filled in already, clear and enter new value
            port = self.driver.find_element_by_id('id_port')
            port.clear()
            port.send_keys(device['port'])

            (self.driver.find_element_by_id('id_username')
                        .send_keys(device['username']))
            (self.driver.find_element_by_id('id_password')
                        .send_keys(device['password']))

            savebtn = self.driver.find_element_by_xpath(
                '//input[@value="Save Changes"]'
            )
            savebtn.click()

            WebDriverWait(self.driver, 5).until(EC.title_contains('Devices'))
            self.assertTrue(self.driver.current_url.endswith('/devices/'))

        # load Overall report
        self.driver.find_element_by_xpath(
            '//ul[@class="nav"]//a[@class="dropdown-toggle"]'
        ).click()
        self.driver.find_element_by_link_text('Overall').click()

        WebDriverWait(self.driver, 5).until(
            EC.title_contains('Overall Report')
        )
        self.assertTrue('Overall Report' in self.driver.title)


class RunOverallReportTests(BaseSeleniumTests):
    """Test that basic reports run successfully."""

    @classmethod
    def setUpClass(cls):
        super(RunOverallReportTests, cls).setUpClass()

        cls.user.profile_seen = True
        cls.user.timezone = settings.TEST_USER_TIMEZONE
        cls.user.save()

        # add devices
        for device in settings.TEST_DEVICES:
            d = Device(**device)
            d.save()

    def test_overall_report(self):
        self.login()

        # wait until we see one of the report pages
        WebDriverWait(self.driver, 5).until(EC.title_contains('Report'))
        self.assertTrue('report' in self.driver.current_url)

        # explicitly load Overall report
        self.driver.find_element_by_xpath(
            '//ul[@class="nav"]//a[@class="dropdown-toggle"]'
        ).click()
        self.driver.find_element_by_link_text('Overall').click()

        WebDriverWait(self.driver, 5).until(
            EC.title_contains('Overall Report')
        )

        # run the report with the default criteria
        run_button = self.driver.find_element_by_id('button-run')
        run_button.click()

        # wait until we see a loading spinner
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME,
                                            'loading-indicator'))
        )

        # wait until the widgets finish loading, look for print-report link
        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            'a#print-report'))
        )

        # validate some of the widget results
        # only three of the four widgets will return
        # the map view should return an error since we don't have geo data
        titles = self.driver.find_elements_by_class_name('wid-title')
        self.assertEqual(len(titles), 3)
