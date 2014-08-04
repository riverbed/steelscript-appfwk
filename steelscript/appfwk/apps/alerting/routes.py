# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
logger = logging.getLogger(__name__)


class BaseRouter(object):
    """Base class for Routers."""
    level = 'warning'

    def __init__(self, *args, **kwargs):
        """Initialize Router service with credentials, etc."""
        pass

    def send(self, alert):
        """Send `alert` to defined router destination."""
        pass


class SmsRouter(BaseRouter):
    pass


class EmailRouter(BaseRouter):
    pass


class LoggingRouter(BaseRouter):
    """Sends results to logger."""
    level = 'info'

    def send(self, alert):
        log = getattr(logger, self.level, 'warning')
        log(alert)


class ConsoleRouter(LoggingRouter):
    """Sends results to console."""
    # XXX experimentally subclassed from LoggingRouter
    def send(self, alert):
        print 'ConsoleRouter: %s' % alert


def find_routers():
    def get_subclasses(c):
        subclasses = c.__subclasses__()
        for d in list(subclasses):
            subclasses.extend(get_subclasses(d))
        return subclasses
    return get_subclasses(BaseRouter)
