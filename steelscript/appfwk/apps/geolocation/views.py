# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import json

from django.http import HttpResponse, Http404
from django.core.exceptions import ObjectDoesNotExist

from steelscript.common.datastructures import DictObject
from steelscript.appfwk.apps.geolocation.models import *
from steelscript.appfwk.apps.geolocation.geoip import LookupIP

# Create your views here.

def getIPAddress(request, addr):
    data = LookupIP.instance().lookup(addr)

    if data:
        return HttpResponse(json.dumps(data))
    else:
        return Http404

def getLocation(request, name):
    try:
        loc = Location.objects.get(name=name);
    except ObjectDoesNotExist:
        return Http404

    d = DictObject()
    d.name = loc.name
    # d.address = loc.address
    # d.mask = loc.mask
    d.latitude = loc.latitude
    d.longitude = loc.longitude

    return HttpResponse(json.dumps(d))
