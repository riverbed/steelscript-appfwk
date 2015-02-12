# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

# avoid SNMP requirements if not using those Senders

try:
    from pysnmp.entity.rfc3413.oneliner import ntforg
    from pysnmp.proto import rfc1902
except ImportError:
    pass

import urllib
import os
import vagrant
import time

from steelscript.common import timeutils
from steelscript.appfwk.apps.alerting.datastructures import AlertLevels
from steelscript.cmdline import cli

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


class SmsSender(BaseSender):
    """Not implemented yet."""
    pass


class EmailSender(BaseSender):
    """Not implemented yet."""
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


class VMBaseSender(BaseSender):
    """Base sender class for spinning up/down vms"""
    def process_alert(self, alert):
        for k, v in (alert.options or {}).iteritems():
            setattr(self, k, v)

    def send(self, alert):
        self.process_alert(alert)
        self.execute()


class BareMetalVMSender(VMBaseSender):
    """Sender class for managing VMs on bare metal machines.
    Note that one instance of this class only maps to one Vagrantfile,
    which is located on one directory at one host. Thus when adding
    destination to your report trigger, it is required to configure
    the host, username, password, directory of vagrantfile, the list
    of vms to start, and the list of vms to shutdown. Note that the
    names of VMs need to match the names in the vagrantfile. If all
    VMs are required to start/shutdown, just put down 'all'. If none
    of VMs are to be strated/shutdown, just do not put up_list/down_list
    in options. An example is shown as below.

    trigger.add_destination(sender='BareMetalVMSender',
                            options={'host' : 'hostname',
                                     'username': 'username',
                                     'password': 'password',
                                     'vagrant_dir': 'directory',
                                     'up_list': ['vm1','vm2],
                                     'down_list': ['vm3','vm4']},
                            template = 'Starting or shutting vms'
                           )
    """
    def __init__(self):
        self._cli = None
        self._running_vms = None
        self._status = {}
        self.up_list = None
        self.down_list = None

    def get_status(self):
        """Return the status of VMs in this directory. Need to parse
        output of 'vagrant status' as below:

        Current machine states:

        web                       poweroff (virtualbox)
        db                        poweroff (virtualbox)

        This environment represents multiple VMs. The VMs are all listed
        above with their current state. For more information about a specific
        VM, run `vagrant status NAME`.
        """
        self._status = {}
        output = self._cli.exec_command('vagrant status')
        output = output.split('\n\n')[1]
        for line in output.split('\n'):
            list = line.split()
            if list[1] == 'running':
                if 'running' not in self._status:
                    self._status['running'] = [list[0]]
                else:
                    self._status['running'].append(list[0])
            elif list[1] == 'poweroff':
                if 'poweroff' not in self._status:
                    self._status['poweroff'] = [list[0]]
                else:
                    self._status['poweroff'].append(list[0])
        return self._status

    def execute(self):

        if self._cli is None:
            self._cli = cli.CLI(hostname=self.host,
                                username=self.username,
                                password=self.password)
            self._cli.start()

        # get in the directory
        if hasattr(self, 'vagrant_dir'):
            self._cli.exec_command('cd %s' % self.vagrant_dir)

        if self.up_list == 'all':
            self._cli.exec_command('vagrant up')
        elif self.up_list:
            self._cli.exec_command('vagrant up %s' % ' '.join(self.up_list))

        if self.down_list == 'all':
            self._cli.exec_command('vagrant halt')
        elif self.down_list:
            self._cli.exec_command('vagrant halt %s' %
                                   ' '.join(self.down_list))

        self.get_status()


class AWSVMSender(VMBaseSender):
    """Not implemented yet"""
    pass


class AzureVMSender(VMBaseSender):
    """Not implemented yet"""
    pass


def find_sender(name):
    return BaseSender.get_sender(name)
