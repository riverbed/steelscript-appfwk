# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902

from steelscript.common import timeutils

import logging
logger = logging.getLogger(__name__)


class RouterMount(type):
    """Metaclass for Router subclasses."""
    # inspired by
    # http://martyalchin.com/2008/jan/10/simple-plugin-framework/
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, '_routers'):
            # setup mount point for class
            cls._routers = dict()
        else:
            # register the class by name
            cls._routers[name] = cls


class BaseRouter(object):
    """Base class for Routers."""
    __metaclass__ = RouterMount

    level = 'warning'

    def __init__(self, *args, **kwargs):
        """Initialize Router service with credentials, etc."""
        pass

    @classmethod
    def get_router(cls, name):
        return cls._routers.get(name, None)

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
    def send(self, alert):
        print 'ConsoleRouter: %s' % alert


class SNMPBaseRouter(BaseRouter):
    """Base class for SNMP trap notifications.

    Subclass this to override defaults and configuration
    """
    # base values for all traps of this class
    community = None     # typically 'public'
    manager_ip = None    # ipaddress of destination server

    # trap-specific items
    eoid = None
    trapid = None
    default_description = 'SteelScript Alert'
    severity = 70
    level = 2

    def process_alert(self, alert):
        """Override class values with kwargs from destination in alert.

        Only predefined attributes can be overwritten, extra or unknown
        values will raise an AttributeError.
        """
        missing = []
        for k, v in alert.destination.iteritems():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                missing.append(k)

        if missing:
            raise AttributeError('Invalid destination keyword arguments: %s '
                                 'for Alert %s' % (missing, alert))

    def send_trap(self):
        ntf = ntforg.NotificationOriginator()
        err = ntf.sendNotification(
            ntforg.CommunityData(self.community),
            ntforg.UdpTransportTarget((self.manager_ip, 162)),
            'trap',
            self.trapname,
            *self.binds
        )
        return err

    def send(self, alert):
        self.process_alert(alert)
        self.setup_snmp_trap(alert)
        self.send_trap()

    def setup_snmp_trap(self):
        """Method for subclasses to override to add logic for specific
        trap implementations.

        Two instance attributes need to be defined from
        this method:
            ``self.trapname`` - this gets passed as the ``notificationType``
                to the underlying snmp library and should be either
                an ObjectIdentifier string, or a MibVariable object.
            ``self.binds`` - array of Managed Objects to construct the
                trap defined in ``self.trapname``.  See example class
                ``SNMPRouterCascadeDefault`` for examples.

        See pysnmp docs for more information here:
            http://pysnmp.sourceforge.net/docs/current/apps/sync-notification-originator.html
        """
        pass


class SNMPRouterCascadeDefault(SNMPBaseRouter):
    """Sends SNMP traps."""
    community = 'public'
    manager_ip = '127.0.0.1'

    eoid = '1.3.6.1.4.1.7054.70.0.'     # Cascade Profile Object ID
    trapid = '99'                       # Test Trap Number
    default_description = 'SteelScript Alert'
    trap_url = 'http://localhost'
    severity = 70
    level = 2

    def setup_snmp_trap(self, alert):
        oid = self.eoid             # cascade enterprise Object ID
        trapid = self.trapid        # base string for trap indicators
        self.trapname = '.'.join([oid, trapid])

        severity = self.severity
        description = alert.message or self.default_description
        alert_level = self.level
        now = timeutils.datetime_to_seconds(alert.timestamp)

        self.binds = (
            ('1.3.6.1.2.1.1.3.0', rfc1902.Integer(0)),                       # Uptime
            ('1.3.6.1.4.1.7054.71.2.1.0', rfc1902.Integer(severity)),        # Severity
            ('1.3.6.1.4.1.7054.71.2.3.0', rfc1902.OctetString(description)),
            ('1.3.6.1.4.1.7054.71.2.4.0', rfc1902.Integer(0)),               # Event ID
            ('1.3.6.1.4.1.7054.71.2.5.0', rfc1902.OctetString(self.trap_url)),
            ('1.3.6.1.4.1.7054.71.2.7.0', rfc1902.Integer(alert_level)),     # Alert Level
            ('1.3.6.1.4.1.7054.71.2.8.0', rfc1902.Integer(now)),             # Start Time
            ('1.3.6.1.4.1.7054.71.2.16.0', rfc1902.Integer(0)),              # Source Count
            ('1.3.6.1.4.1.7054.71.2.18.0', rfc1902.Integer(0)),              # Destination Count
            ('1.3.6.1.4.1.7054.71.2.20.0', rfc1902.Integer(0)),              # Protocol Count
            ('1.3.6.1.4.1.7054.71.2.22.0', rfc1902.Integer(0)),              # Port Count
        )


def find_router(name):
    return BaseRouter.get_router(name)
