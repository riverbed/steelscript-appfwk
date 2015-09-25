# Copyright (c) 2015 Riverbed Technology, Inc.
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
        self.verify()


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

    def __init__(self):
        # Attributes that come from alerts
        self.host = None          # host/ip for the bare metal host of VMs
        self.username = None      # username to access the host
        self.password = None      # password to access the host
        self.vagrant_dir = None   # directory of the vagrant file
        self.up_list = []         # list of VM names to start (optional)
        self.down_list = []       # list of VM names to shutdown (optional)
        self.timeout = 300        # max time in seconds for vagrant commands

        # Internal attributes
        self._cli = None
        self._status = {}
        self._cd_dir = ''
        self._running_vms = None
        self._non_running_vms = None

    def vagrant(self, args):
        """Execute a vagrant command

        :param command: a list of arguments/options in a vagrant command
        """
        command = self._cd_dir + 'vagrant ' + ' '.join(args)
        logger.debug("Executing command '%s' timeout %d" %
                     (command, self.timeout))

        return self._cli.exec_command(command, timeout=self.timeout)

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
        self._running_vms = []
        self._non_running_vms = []

        output = self.vagrant(['status'])
        output = output.split('\n\n')[1]
        for line in output.split('\n'):
            # parsing each line as
            # 'vmname                     state (provider)'
            # state is one of
            # ['running', 'poweroff', 'aborted', 'not created']

            list = line.split()
            if list[-2] == 'created' and list[-3] == 'not':
                state = 'not created'
            else:
                state = list[-2]

            # remove trailing white spaces
            vm_name = line[:-line.find(state)].rstrip()

            self._status[vm_name] = state

            # cache running vms to verify success easily
            if state == 'running':
                self._running_vms.append(vm_name)
            else:
                self._non_running_vms.append(vm_name)

        if not self._status:
            # no vm is found, raise environment error
            raise EnvironmentError("No vm is found while deriving status")

        logger.debug("the status of VMs are %s " % self._status)

    def execute(self):

        if self._cli is None:
            self._cli = Shell(host=self.host,
                              user=self.username,
                              password=self.password)

        if self.vagrant_dir:
            self._cd_dir = 'cd %s;' % self.vagrant_dir

        if self.up_list == 'all':
            self.vagrant(['up'])
        elif self.up_list:
            self.vagrant(['up'] + ["'%s'" % vm for vm in self.up_list])

        if self.down_list == 'all':
            self.vagrant(['halt'])
        elif self.down_list:
            self.vagrant(['halt'] + ["'%s'" % vm for vm in self.down_list])

    def verify(self):
        "Verify the VMs are at correct states after execution"

        failure = False

        self.get_status()

        # check all vms in down_list are not running
        to_be_down_vms = (self._status.keys() if self.down_list == 'all'
                          else self.down_list)

        if not set(to_be_down_vms).issubset(set(self._non_running_vms)):
            failure = True

        # check all vms in up_list minus down_list are not running
        # as shutdown execution is implemented after the start operation
        # there can be vms started first then being shutdown after
        up_vms = self._status.keys() if self.up_list == 'all' else self.up_list
        to_be_up_vms = set(up_vms) - set(to_be_down_vms)

        if not to_be_up_vms.issubset(set(self._running_vms)):
            failure = True

        msg = (" in running vagrant command on host: %s, dir: %s, "
               "the list vms to be started is %s, "
               "the list of actual running vms is %s, "
               "the list vms to be shut down is %s, "
               "the list of actual non-running vms is %s." %
               (self.host, self.vagrant_dir,
                list(to_be_up_vms), self._running_vms,
                to_be_down_vms, self._non_running_vms))

        if failure:
            logger.error("Failure" + msg)
        else:
            logger.info("Success" + msg)


class AWSVMSender(VMBaseSender):
    """Not implemented yet"""
    pass


class AzureVMSender(VMBaseSender):
    """Not implemented yet"""
    pass
