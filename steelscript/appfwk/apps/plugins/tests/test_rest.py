# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from mock import Mock, patch
from django.test import TestCase
from django.core import management
from django.core.exceptions import ObjectDoesNotExist

from steelscript.appfwk.apps.preferences.models import AppfwkUser

from steelscript.appfwk.apps.plugins import plugins

logger = logging.getLogger(__name__)


class MockPlugin(object):
    def __init__(self, slug):
        self.enabled = True
        self.title = slug

    def get_namespace(self):
        return None

    @property
    def __dict__(self):
        return {'a': 1}


class PluginRestTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            AppfwkUser.objects.get(username='admin')
        except ObjectDoesNotExist:
            AppfwkUser.objects.create_superuser(
                'admin', 'admin@admin.com', 'admin')

    def setUp(self):
        self.slug = "plugin_slug"
        logger.info('Logging in as admin')
        # Setting HTTP_ACCEPT to require json response
        self.assertTrue(self.client.login(username='admin', password='admin'))
        plugins.get = Mock(return_value=MockPlugin(self.slug))

    def test_plugin_detail(self):
        with patch('steelscript.appfwk.apps.plugins.views.set_reports',
                   Mock(return_value=["test_reports"])):
            url = '/plugins/%s/' % self.slug
            response = self.client.post(url, {'enabled': True})
            self.assertEqual(response.status_code, 200)

    def test_plugin_collect(self):
        management.call_command = Mock(return_value=None)
        url = '/plugins/collect/'
        response = self.client.get(url, {'overwrite': True})
        self.assertEqual(response.status_code, 200)

        url = '/plugins/plugin_slug/collect/'
        response = self.client.get(url, {'overwrite': True})
        self.assertEqual(response.status_code, 200)
