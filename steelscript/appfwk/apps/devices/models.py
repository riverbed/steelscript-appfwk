# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import json
import logging
from cStringIO import StringIO

from django.db import models
from django.core import management
from django.conf import settings

from steelscript.common import Auth

logger = logging.getLogger(__name__)


def create_device_fixture(strip_passwords=True):
    """ Dump devices to JSON file, optionally stripping passwords.

    If password is stripped, the device is disabled.
    """
    buf = StringIO()
    management.call_command('dumpdata', 'devices', stdout=buf)
    buf.seek(0)
    devices = list()
    for d in json.load(buf):
        if strip_passwords:
            del d['fields']['password']
            del d['fields']['access_code']
            d['fields']['enabled'] = False
        devices.append(d)

    buf.close()

    fname = os.path.join(settings.INITIAL_DATA, 'initial_devices.json')
    with open(fname, 'w') as f:
        f.write(json.dumps(devices, indent=2))

    logger.debug('Wrote %d devices to fixture file %s' % (len(devices), fname))


class Device(models.Model):
    """ Records for devices referenced in report configuration pages.

        Actual instantiations of Device objects handled through DeviceManager
        class in devicemanager.py module.
    """
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)
    host = models.CharField(max_length=200)
    port = models.IntegerField(default=443)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)

    auth = models.IntegerField(
        default=Auth.NONE,
        choices=((Auth.NONE, 'None'),
                 (Auth.BASIC, 'Basic'),
                 (Auth.OAUTH, 'OAuth2'))
    )

    access_code = models.TextField(blank=True)

    # only enabled devices will require field validation
    enabled = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s (%s:%s)' % (self.name, self.host, self.port)

    def save(self, *args, **kwargs):
        super(Device, self).save(*args, **kwargs)
        create_device_fixture(settings.APPFWK_STRIP_DEVICE_PASSWORDS)
