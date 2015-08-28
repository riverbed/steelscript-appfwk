# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import logging


from django.test import TestCase, Client
from django.core.exceptions import ObjectDoesNotExist

from steelscript.appfwk.apps.preferences.models import (AppfwkUser,
                                                        SystemSettings)

logger = logging.getLogger(__name__)


class PreferencesTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            AppfwkUser.objects.get(username='admin')
        except ObjectDoesNotExist:
            AppfwkUser.objects.create_superuser(
                'admin', 'admin@admin.com', 'admin')

    def setUp(self):
        logger.info('Logging in as admin')
        self.client = Client()
        self.assertTrue(self.client.login(username='admin', password='admin'))

    def post_escape_keyerror(self, data):
        """Escape the exception of missing 'HTTP_REFERER' in header"""
        try:
            self.client.post(self.url, data=data)
        except KeyError, e:
            if e.message != 'HTTP_REFERER':
                raise e


class AppfwkUserTestCase(PreferencesTestCase):
    url = '/preferences/user/'

    def test_default(self):
        user = AppfwkUser.objects.get(username='admin')
        self.assertEqual(user.timezone, 'UTC')
        self.assertEqual(user.timezone_changed, False)
        self.assertEqual(user.profile_seen, False)

    def test_profile_seen(self):
        self.client.get(self.url)
        user = AppfwkUser.objects.get(username='admin')
        self.assertEqual(user.profile_seen, True)

    def test_timezone_changed(self):
        timezone = "US/Eastern"
        email = "newuser@test.com"
        data = {'timezone': timezone, 'email': email}
        self.post_escape_keyerror(data)

        # could not set user.timezone_changed as True
        # thus only test timezone and email are updated
        user = AppfwkUser.objects.get(username='admin')
        self.assertEqual(user.timezone, timezone)
        self.assertEqual(user.email, email)


class SystemSettingsTestCase(PreferencesTestCase):
    url = '/preferences/system/'

    def test_singleton(self):
        obj1 = SystemSettings.get_system_settings()
        obj2 = SystemSettings.get_system_settings()
        self.assertEqual(obj1, obj2)

    def test_save(self):
        SystemSettings().save()
        objs = SystemSettings.objects.all()
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].pk, 1)

    def test_default(self):
        obj = SystemSettings.get_system_settings()
        self.assertEqual(obj.ignore_cache, False)
        self.assertEqual(obj.developer, False)
        self.assertEqual(obj.maps_version, 'OPEN_STREET_MAPS')
        self.assertEqual(obj.maps_api_key, None)
        self.assertEqual(obj.global_error_handler, True)

    def test_post(self):
        setting = {'ignore_cache': True,
                   'developer': True,
                   'maps_version': 'FREE',
                   'maps_api_key': 'key',
                   'global_error_handler': False
                   }
        self.post_escape_keyerror(setting)
        setting = SystemSettings.get_system_settings()
        self.assertTrue(setting.ignore_cache)
        self.assertTrue(setting.developer)
        self.assertEqual(setting.maps_version, 'FREE')
        self.assertEqual(setting.maps_api_key, 'key')
        self.assertFalse(setting.global_error_handler)
