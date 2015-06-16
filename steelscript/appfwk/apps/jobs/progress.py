import logging
from django.conf import settings

from steelscript.common.connection import Connection


logger = logging.getLogger(__name__)


class ProgressDaemon(object):
    def __init__(self):
        self.conn = Connection(settings.PROGRESSD_HOST,
                               port=settings.PROGRESSD_PORT)

    def get(self, id_, attr=None):
        r = self.conn.json_request('GET', '/jobs/%d/' % id_)
        if attr:
            return r[attr]
        return r

    def post(self, **kwargs):
        return self.conn.json_request('POST', '/jobs/', body=kwargs)
        pass

    def put(self, id_, **kwargs):
        self.conn.json_request('PUT', '/jobs/%d/' % id_, body=kwargs)

    def delete(self, id_):
        self.conn.json_request('DELETE', '/jobs/%d/' % id_)


progressd = ProgressDaemon()
