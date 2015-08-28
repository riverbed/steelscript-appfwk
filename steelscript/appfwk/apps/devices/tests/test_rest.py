# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import copy

from django.test import TestCase, Client
from django.core.exceptions import ObjectDoesNotExist

from steelscript.appfwk.apps.preferences.models import AppfwkUser

logger = logging.getLogger(__name__)


class DeviceRestTestCase(TestCase):
    device = {"name": "profiler",
              "module": "netprofiler",
              "host": "host.profiler.com",
              "port": 443,
              "username": "admin",
              "password": "password",
              "enabled": True,
              "auth": 1,
              "access_code": ''
              }

    @classmethod
    def setUpClass(cls):
        try:
            AppfwkUser.objects.get(username='admin')
        except ObjectDoesNotExist:
            AppfwkUser.objects.create_superuser(
                'admin', 'admin@admin.com', 'admin')

    def setUp(self):
        logger.info('Logging in as admin')
        # Setting HTTP_ACCEPT to require json response
        self.client = Client(HTTP_ACCEPT='application/json')
        self.assertTrue(self.client.login(username='admin', password='admin'))

    def _get_device(self, device_id):
        """Obtain the device data as a dict based on device id.

        :param device_id: integer representing the unique id
        """
        url = '/devices/%s/' % device_id
        response = self.client.get(url)
        if response.status_code == 200:
            return self._fix_dev(response.data)

        self.assertEqual(response.status_code, 404)
        return None

    def _fix_dev(self, device):
        if 'id' in device:
            del device['id']
        return device

    def _add_device(self, data):
        """Add a new device's data to the db.

        :param data: python dict representing a device
        """
        url = '/devices/add/'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)

    def _modify_device(self, data, device_id):
        """Modify a exiting device's data

        :param data: python dict representing device to overwrite
        :param device_id: integer representing the device to be be modified
        """
        url = '/devices/%s/' % device_id
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)

    def _delete_device(self, device_id):
        url = '/devices/%s/' % device_id
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_device_detail(self):
        """Testing function for class devices/views/DeviceDetail"""

        url = '/devices/add/'
        response = self.client.get(url)
        # no device id, thus 404 is generated
        self.assertEqual(response.status_code, 404)

        self._add_device(self.device)
        # Checking the data fetched is the same as written
        self.assertEqual(self.device, self._get_device(1))

        # Modify the device's data
        device = self._get_device(1)
        device['name'] = 'profiler1'
        self._modify_device(device, 1)
        self.assertEqual(device, self._get_device(1))

        # Delete the device's data
        self._delete_device(1)
        self.assertEqual(self._get_device(1), None)

    def test_device_list(self):
        """Testing function for class devices/views/DeviceList"""

        self._add_device(self.device)
        device1 = copy.copy(self.device)
        device1['name'] = 'profiler1'
        self._add_device(device1)

        url = '/devices/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        dev_list = [self._fix_dev(dev) for dev in response.data]
        self.assertEqual(self.device, dev_list[0])
        self.assertEqual(device1, dev_list[1])
