# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.alerting.datastructures import AlertLevels

import logging
logger = logging.getLogger(__name__)


class SenderMount(type):
    """Metaclass for Sender subclasses."""
    # inspired by
    # http://martyalchin.com/2008/jan/10/simple-plugin-framework/
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, '_senders'):
            # setup mount point for class
            cls._senders = dict()
        else:
            # register the class by name
            if (name in cls._senders and
                    cls._senders[name].__module__ != cls.__module__):
                msg = 'Sender class %s has already been defined' % name
                raise ValueError(msg)
            cls._senders[name] = cls


class BaseSender(object):
    """Base class for Senders."""
    __metaclass__ = SenderMount

    level = AlertLevels.WARNING

    def __init__(self, *args, **kwargs):
        """Initialize Sender service with credentials, etc."""
        pass

    @classmethod
    def get_sender(cls, name):
        return cls._senders.get(name, None)

    def send(self, alert):
        """Send `alert` to defined sender destination."""
        pass


class LoggingSender(BaseSender):
    """Sends results to logger at default 'warning' level."""
    def send(self, alert):
        log = getattr(logger, alert.level.lower())
        log(alert.message)


class ConsoleSender(LoggingSender):
    """Sends results to console."""
    def send(self, alert):
        print 'ConsoleSender: %s - %s' % (alert.level, alert)
