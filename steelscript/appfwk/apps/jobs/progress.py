# Copyright (c) 2014-2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
from django.conf import settings

from steelscript.common.connection import Connection


logger = logging.getLogger(__name__)


class ProgressDaemon(object):
    def __init__(self):
        self.conn = Connection(settings.PROGRESSD_HOST,
                               port=settings.PROGRESSD_PORT)

    def get(self, id_, attr=None):
        r = self.conn.json_request('GET', '/jobs/items/%d/' % id_)
        if attr:
            return r[attr]
        return r

    def post(self, **kwargs):
        return self.conn.json_request('POST', '/jobs/', body=kwargs)
        pass

    def put(self, id_, **kwargs):
        self.conn.json_request('PUT', '/jobs/items/%d/' % id_, body=kwargs)

    def delete(self, id_):
        self.conn.json_request('DELETE', '/jobs/items/%d/' % id_)

    def reset(self):
        self.conn.json_request('POST', '/jobs/reset/')


progressd = ProgressDaemon()
