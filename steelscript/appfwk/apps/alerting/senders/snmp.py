# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


try:
    from pysnmp.entity.rfc3413.oneliner import ntforg
    from pysnmp.proto import rfc1902
except ImportError:
    pass

import urllib

from steelscript.common import timeutils
from steelscript.appfwk.apps.alerting.senders.base import BaseSender
from steelscript.appfwk.apps.alerting.datastructures import AlertLevels


class SNMPBaseSender(BaseSender):
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
    level = AlertLevels.INFO

    def process_alert(self, alert):
        """Override class values with kwargs from destination in alert.

        Only predefined attributes can be overwritten, extra or unknown
        values will raise an AttributeError.
        """
        missing = []
        for k, v in (alert.options or {}).iteritems():
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

    def setup_snmp_trap(self, alert):
        """Method for subclasses to override to add logic for specific
        trap implementations.

        Two instance attributes need to be defined from
        this method:
            ``self.trapname`` - this gets passed as the ``notificationType``
                to the underlying snmp library and should be either
                an ObjectIdentifier string, or a MibVariable object.
            ``self.binds`` - array of Managed Objects to construct the
                trap defined in ``self.trapname``.  See example class
                ``SNMPSenderCascadeDefault`` for examples.

        See pysnmp docs for more information here:
            http://pysnmp.sourceforge.net/docs/current/apps/sync-notification-originator.html
        """
        pass


class SNMPSenderSteelScript(SNMPBaseSender):
    """Sends SNMP traps."""

    eoid = '1.3.6.1.4.1.17163.1.500'     # SteelScript OID
    trapid = '1.0.2'                     # Test Trap Number
    default_description = 'SteelScript Alert'
    trap_url = 'http://localhost'

    def setup_snmp_trap(self, alert):
        oid = self.eoid             # cascade enterprise Object ID
        trapid = self.trapid        # base string for trap indicators
        self.trapname = '.'.join([oid, trapid])

        context = urllib.urlencode(alert.event.trigger_result)
        eid = alert.event.eventid

        self.binds = (
            # eventID == UUID
            ('1.3.6.1.4.1.17163.1.500.1.1.1', rfc1902.OctetString(eid)),

            # eventContext
            ('1.3.6.1.4.1.17163.1.500.1.1.4', rfc1902.OctetString(context)),
        )


class SNMPSenderCascadeDefault(SNMPBaseSender):
    """Sends SNMP traps."""
    community = 'public'
    manager_ip = '127.0.0.1'

    eoid = '1.3.6.1.4.1.7054.70.0.'     # Cascade Profile Object ID
    trapid = '99'                       # Test Trap Number
    default_description = 'SteelScript Alert'
    trap_url = 'http://localhost'
    severity = 70
    level = AlertLevels.INFO

    def setup_snmp_trap(self, alert):
        oid = self.eoid             # cascade enterprise Object ID
        trapid = self.trapid        # base string for trap indicators
        self.trapname = '.'.join([oid, trapid])

        severity = self.severity
        description = alert.message or self.default_description
        alert_level = AlertLevels.get_integer(self.level)
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
