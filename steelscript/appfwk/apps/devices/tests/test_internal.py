# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import unittest
import sys
import copy

from mock import patch, Mock
from steelscript.appfwk.apps.devices.models import Device
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.plugins import plugins
from steelscript.appfwk.apps.devices.exceptions import DeviceModuleNotFound


class MockDevice(object):
    def __init__(self, host='', port=None, auth=None):
        self.host = host
        self.port = port
        self.auth = auth


class DeviceManagerTestCase(unittest.TestCase):

    dev = {'id': 1,
           'name': 'dev_name',
           'module': 'dev_module',
           'host': 'dev_host',
           'port': 443,
           'username': 'user',
           'password': 'pass',
           'auth': 1,
           'access_code': ''
           }

    devices = [('dev_module', 'dev_pkg')]

    def setUp(self):
        dev = Device(**self.dev)
        dev.save()
        self.stash = plugins.devices
        plugins.devices = Mock(return_value=self.devices)
        sys.modules['dev_pkg'] = Mock()

    def tearDown(self):
        Device.objects.all().delete()
        del sys.modules['dev_pkg']
        plugins.devices = self.stash

    def test_get_devices(self):
        with patch("dev_pkg.new_device_instance", MockDevice):
            device = DeviceManager.get_device(1)

        self.assertEqual(device.host, self.dev['host'])
        self.assertEqual(device.port, self.dev['port'])
        self.assertEqual(device.auth.username, self.dev['username'])
        self.assertEqual(device.auth.password, self.dev['password'])

    def test_get_devices_with_unknown_module(self):
        dev = copy.copy(self.dev)
        dev['id'] = 2
        dev['module'] = 'unknown_module'
        dev_obj = Device(**dev)
        dev_obj.save()
        with self.assertRaises(DeviceModuleNotFound):
            DeviceManager.get_device(2)

    def test_clear(self):
        DeviceManager.clear()
        self.assertEqual(DeviceManager.devices, {})

    def test_clear_with_device_id(self):
        DeviceManager.clear(device_id=1)
        self.assertFalse(1 in DeviceManager.devices)

    def test_get_modules(self):
        self.assertTrue('dev_module' in DeviceManager.get_modules())
