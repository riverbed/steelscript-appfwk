# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import time
import logging

from django.conf import settings
from requests import ConnectionError

from steelscript.common.connection import Connection
from steelscript.common import RvbdException


logger = logging.getLogger(__name__)


class ProgressDaemon(object):
    def __init__(self):
        self.conn = Connection(settings.PROGRESSD_HOST,
                               port=settings.PROGRESSD_PORT)

    def _request(self, method, url, **kwargs):
        try:
            return self.conn.json_request(method, url, **kwargs)
        except ConnectionError:
            # In case progressd is restarting due to daily logrotate
            # resending the request after 10 seconds
            logger.warning("Waiting %s seconds before reconnecting progressd"
                           % settings.PROGRESSD_CONN_TIMEOUT)
            time.sleep(settings.PROGRESSD_CONN_TIMEOUT)
            try:
                return self.conn.json_request(method, url, **kwargs)
            except ConnectionError:
                raise RvbdException(
                    "Error connecting to appfwk service 'progressd': "
                    "try restarting the service "
                    "(sudo service progressd restart) "
                    "or contact your administrator for assistance."
                )

    def get(self, id_, attr=None):
        r = self._request('GET', '/jobs/items/%d/' % id_)
        if attr:
            return r[attr]
        return r

    def post(self, **kwargs):
        return self._request('POST', '/jobs/', body=kwargs)

    def put(self, id_, **kwargs):
        self._request('PUT', '/jobs/items/%d/' % id_, body=kwargs)

    def delete(self, id_):
        self._request('DELETE', '/jobs/items/%d/' % id_)

    def reset(self):
        self._request('POST', '/jobs/reset/')


progressd = ProgressDaemon()
