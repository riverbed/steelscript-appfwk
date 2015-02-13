# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


try:
    from steelscript.cmdline.shell import Shell
except:
    pass

from steelscript.appfwk.apps.alerting.senders.base import BaseSender

import logging
logger = logging.getLogger(__name__)


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
                                     'down_list': 'all',
                                     'timeout':300},
                            template = 'Starting or shutting vms'
                           )
    """
    STATES = ['running', 'poweroff', 'aborted', 'not created']

    def __init__(self):
        self._cli = None
        self._status = {}
        self.up_list = None
        self.down_list = None

    def vagrant(self, args):
        """Execute a vagrant command

        :param command: a list of arguments/options in a vagrant command
        """
        command = self.cd_dir + 'vagrant ' + ' '.join(args)
        timeout = self.timeout if hasattr(self, 'timeout') else 60
        logger.debug("Executing command '%s' timeout %d" % (command, timeout))

        return self._cli.exec_command(command, timeout=timeout)

    def get_status(self):
        """Return the status of VMs in this directory. Need to parse
        output of 'vagrant status' as below:

        Current machine states:

        web                       poweroff (virtualbox)
        db                        poweroff (virtualbox)

        This environment represents multiple VMs. The VMs are all listed
        above with their current state. For more information about a
        specific VM, run `vagrant status NAME`.
        """
        self._status = {}
        try:
            output = self.vagrant(['status'])
            output = output.split('\n\n')[1]
            for line in output.split('\n'):
                list = line.split()
                if list[1] == 'not' and list[2] == 'created':
                    state = 'not created'
                else:
                    state = list[1]

                if state in self.STATES:
                    if state not in self._status:
                        self._status[state] = [list[0]]
                    else:
                        self._status[state].append(list[0])
            if not self._status:
                # None VMs are found to be a valid, as one of STATES
                # raise environment error
                raise

            logger.debug("the status of VMs are %s " % self._status)
        except:
            raise EnvironmentError("Failed to obtain status for VMs from"
                                   " output of 'vagrant status' as below.\n"
                                   "\n %s " % output)

    def execute(self):

        if self._cli is None:
            self._cli = Shell(host=self.host,
                              user=self.username,
                              password=self.password)

        self.cd_dir = 'cd %s; ' % (self.vagrant_dir
                                   if hasattr(self, 'vagrant_dir') else '')

        if self.up_list == 'all':
            self.vagrant(['up'])
        elif self.up_list:
            self.vagrant(['up'] + self.up_list)

        if self.down_list == 'all':
            self.vagrant(['halt'])
        elif self.down_list:
            self.vagrant(['halt'] + self.down_list)

        self.get_status()


class AWSVMSender(VMBaseSender):
    """Not implemented yet"""
    pass


class AzureVMSender(VMBaseSender):
    """Not implemented yet"""
    pass
