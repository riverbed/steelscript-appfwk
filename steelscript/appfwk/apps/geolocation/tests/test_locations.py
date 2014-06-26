import os
import logging
from cStringIO import StringIO

from django.test import TestCase
from django.core import management

from steelscript.appfwk.apps.geolocation.models import Location, LocationIP

logger = logging.getLogger(__name__)


class LocationTestCase(TestCase):

    def setUp(self):
        self.locfile = os.path.join(os.path.dirname(__file__),
                                    '../sample_locations.txt')
        self.locipfile = os.path.join(os.path.dirname(__file__),
                                      '../sample_location_ip.txt')

    def assert_locations_len(self, num):
        locations = Location.objects.all()
        self.assertTrue(len(locations) == num)

    def assert_locations_ip_len(self, num):
        locations_ip = LocationIP.objects.all()
        self.assertTrue(len(locations_ip) == num)

    def call_locations(self, locs=None, locs_ip=None, merge=False):
        buf = StringIO()
        management.call_command('locations', import_locations=locs, import_location_ip=locs_ip,
                                merge=merge, stdout=buf)
        buf.seek(0)
        return buf

    def test_locations_empty(self):
        self.assert_locations_len(0)
        self.assert_locations_ip_len(0)

    def test_locations_import(self):
        self.call_locations(locs=self.locfile)
        self.assert_locations_len(13)
        self.assert_locations_ip_len(0)

    def test_locations_ip_import_error(self):
        # no existing location for the ip to be added
        self.assertRaises(KeyError, self.call_locations, locs_ip=self.locipfile)

    def test_import_nomerge(self):
        self.call_locations(locs=self.locfile, locs_ip=self.locipfile)
        self.assert_locations_len(13)
        self.assert_locations_ip_len(13)

    def test_import_merge(self):
        self.test_import_nomerge()
        buf = self.call_locations(self.locfile, self.locipfile, True)
        self.assertTrue('updated' in buf.read())
        self.assert_locations_len(13)
        self.assert_locations_ip_len(13)
