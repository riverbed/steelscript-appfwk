# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import socket
import threading

import pygeoip
from pygeoip.util import ip2long

from steelscript.common.datastructures import DictObject


GEOLOCATION_DATA_FILE = '/tmp/GeoLiteCity.dat1'
lookup_lock = threading.Lock()

class LookupLocation(object):
    _singleton = None

    @classmethod
    def instance(cls):
        with lookup_lock:
            if cls._singleton is None:
                cls._singleton = LookupLocation()

        return cls._singleton

    def lookup(self, addr):
        addrlong = ip2long(addr)

        data = DictObject()
        data.addr = addr

        for location_ip in LocationIP.objects.all():
            if ((addrlong & ip2long(location_ip.mask)) == ip2long(location_ip.address)):
                location = location_ip.location
                data.latitude = location.latitude
                data.longitude = location.longitude
                data.name = location.name
                match = True
                break

        if match:
            return data
        else:
            return None


class LookupIP(object):
    _singleton = None

    def __init__(self):
        if not os.path.exists(GEOLOCATION_DATA_FILE):
            raise ValueError("Please download the city database from http://dev.maxmind.com/geoip/install/city and save at %s" % GEOLOCATION_DATA_FILE)

        geolite_dat = os.path.expanduser(GEOLOCATION_DATA_FILE)
        self.geoip = pygeoip.GeoIP(geolite_dat, pygeoip.MEMORY_CACHE)

    @classmethod
    def instance(cls):
        with lookup_lock:
            if cls._singleton is None:
                cls._singleton = Lookup()

        return cls._singleton

    def lookup(self, addr):
        data = DictObject()
        data.addr = addr

        with lookup_lock:
            r = self.geoip.record_by_addr(addr)

        match = False

        if r is not None:
            data.latitude = r['latitude']
            data.longitude = r['longitude']
            match = True
            try:
                (n, x, y) = socket.gethostbyaddr(addr)
                data.name = n
            except:
                data.name = addr

            return data
        else:
            return None
