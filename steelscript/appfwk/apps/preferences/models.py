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
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import pytz


logger = logging.getLogger(__name__)


#######################################################################
#
# User Preferences
#
TIMEZONE_CHOICES = zip(pytz.common_timezones, pytz.common_timezones)

MAPS_VERSIONS = ('DISABLED',
                 'DEVELOPER',           # Google Maps Versions
                 'FREE',
                 'BUSINESS',
                 'OPEN_STREET_MAPS',    # Open Street Maps
                 #'STATIC_MAPS'          # Static library created maps
                 )
MAPS_VERSION_CHOICES = zip(MAPS_VERSIONS, map(str.title, MAPS_VERSIONS))


def create_preference_fixture(initial_admin_only=True):
    """Dump preferences to JSON file for safe keeping.

    Marks all preference objects as "not seen" so they will still
    appear after a reset to confirm choices.

    `initial_admin_only` set to True will only store preferences
    where the user id exists in the initial_admin_user file to
    avoid conflicts on database reloads.
    """
    buf = StringIO()
    management.call_command('dumpdata', 'preferences', stdout=buf)
    buf.seek(0)
    preferences = list()

    if initial_admin_only:
        admin_file = os.path.join(settings.PROJECT_ROOT,
                                  'initial_data',
                                  'initial_admin_user.json')
        with open(admin_file) as f:
            admin_ids = set(x['pk'] for x in json.load(f))

        for pref in json.load(buf):
            pref['fields']['profile_seen'] = False
            if pref['fields']['user'] in admin_ids:
                preferences.append(pref)

    else:
        for pref in json.load(buf):
            pref['fields']['profile_seen'] = False
            preferences.append(pref)

    buf.close()

    fname = os.path.join(settings.PROJECT_ROOT,
                         'initial_data',
                         'initial_preferences.json')

    with open(fname, 'w') as f:
        f.write(json.dumps(preferences, indent=2))

    logger.debug('Wrote %d preferences to fixture file %s' % (len(preferences),
                                                              fname))


class AppfwkUser(AbstractUser):
    """ Extend base user class with additional profile prefs. """
    timezone = models.CharField(max_length=50,
                                default='UTC',
                                choices=TIMEZONE_CHOICES,
                                verbose_name='Local Timezone',
                                help_text='Choose the timezone '
                                          'that best matches your current '
                                          'browser location')

    # hidden fields
    timezone_changed = models.BooleanField(default=False)
    profile_seen = models.BooleanField(default=False)


class SystemSettings(models.Model):
    """ Global system preferences, configured by admin user. """
    # implemented as a singleton instance
    # investigate using package like django-solo for more features

    ignore_cache = models.BooleanField(
        default=False,
        help_text='Force all reports to bypass cache'
    )
    developer = models.BooleanField(
        default=False,
        verbose_name='developer mode',
        help_text='Enable additional debug features',
    )
    maps_version = models.CharField(
        max_length=30,
        verbose_name='Maps Version',
        choices=MAPS_VERSION_CHOICES,
        default='DISABLED'
    )
    maps_api_key = models.CharField(
        max_length=100,
        verbose_name='Maps API Key',
        blank=True,
        null=True
    )
    weather_enabled = models.BooleanField(
        default=False,
        help_text='Enable or disable the weather map tiles'
    )
    weather_url = models.CharField(
        max_length=500,
        verbose_name='URL for weather map tiles',
        blank=True,
        null=True
    )
    global_error_handler = models.BooleanField(
        default=True,
        help_text='Apply global error handlers',
        verbose_name='Global Error Handlers'
    )

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SystemSettings, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_system_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
