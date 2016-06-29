# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from steelscript.appfwk.apps.hitcount.models import Hitcount


class CounterMiddleware(object):
    """ Middleware to count uri visits. """

    def process_request(self, request):
        Hitcount.objects.add_uri_visit(request, request.path_info)
