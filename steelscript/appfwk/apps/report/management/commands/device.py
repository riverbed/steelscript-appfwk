# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import sys

from django.core.management.base import BaseCommand

from steelscript.common.datautils import Formatter

from steelscript.appfwk.apps.devices.models import Device

REQUIRED_DEVICE_ATTRS = ['host', 'module', 'name', 'username', 'password']
DEVICE_ATTRS = REQUIRED_DEVICE_ATTRS + ['enabled', 'port']


class Command(BaseCommand):
    args = None
    help = 'Add, modify, delete and display device objects'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('--list',
                          action='store_true',
                          dest='device_list',
                          default=False,
                          help='List of all available devices')

        parser.add_option('--add',
                          action='store_true',
                          dest='add_device',
                          default=False,
                          help=('Add one device to the database. '
                                'For example:\n'
                                './manage.py device --add -H host -M module '
                                '-N name -p port -U user -P password '
                                '-E True'))

        parser.add_option('--edit',
                          action='store_true',
                          dest='edit_device',
                          default=False,
                          help=('Edit one device identified by id. '
                                'For example:\n'
                                './manage.py device --edit -I 1 '
                                '-N new_name'))

        parser.add_option('-H', '--host', help='Hostname or IP address')
        parser.add_option('-M', '--module', help='Module name for the device')
        parser.add_option('-N', '--name', help='Name of the device')
        parser.add_option('-p', '--port', help='Port of the device to connect')
        parser.add_option('-E', '--enabled', help='If the device is enabled')
        parser.add_option('-U', '--username', help='Username for the device')
        parser.add_option('-P', '--password', help='Password for the device')
        parser.add_option('-I', '--id', help='ID of a device to be edited')

        return parser

    def handle(self, *args, **options):
        """ Main command handler. """
        if options['device_list']:
            output = []
            for d in Device.objects.all():
                output.append([d.id, d.name, d.module, d.host, d.port,
                               d.username, d.enabled])
            Formatter.print_table(output, ['ID', 'Name', 'Module', 'Host',
                                           'Port', 'User Name', 'Enabled'])

        elif options['add_device']:
            dev = {}
            for opt in REQUIRED_DEVICE_ATTRS:
                if options[opt] is None:
                    self.stdout.write("Option '%s' is required for a device" %
                                      opt)
                    sys.exit(1)
                dev[opt] = options[opt]

            if options['port']:
                if options['port'].isdigit():
                    dev['port'] = int(options['port'])
                else:
                    self.stdout.write("Option port '%s' is not a positive "
                                      "integer" % options['port'])
                    sys.exit(1)

            if options['enabled']:
                if options['enabled'].lower() == 'false':
                    dev['enabled'] = False
                else:
                    dev['enabled'] = True

            dev_obj = Device(**dev)
            dev_obj.save()
            self.stdout.write('Device added.')

        elif options['edit_device']:

            if not options['id']:
                self.stdout.write('Option ID is required to edit a device')
                sys.exit(1)

            elif not options['id'].isdigit():
                self.stdout.write("Option id '%s' is not a positive integer" %
                                  options['id'])
                sys.exit(1)

            dev_list = Device.objects.filter(id=int(options['id']))
            if not dev_list:
                self.stdout.write("Option id '%s' does not match a device" %
                                  options['id'])
                sys.exit(1)

            if options['port']:
                if options['port'].isdigit():
                    options['port'] = int(options['port'])
                else:
                    self.stdout.write("Option port '%s' is not a positive "
                                      "integer" % options['port'])
                    sys.exit(1)

            if options['enabled']:
                if options['enabled'].lower() == 'false':
                    options['enabled'] = False
                else:
                    options['enabled'] = True

            dev_obj = dev_list[0]
            change = False
            for attr in DEVICE_ATTRS:
                if options[attr] is not None:
                    change = True
                    setattr(dev_obj, attr, options[attr])

            if change:
                dev_obj.save()
                self.stdout.write("Device '%s' modified" % options['id'])
            else:
                self.stdout.write("Device '%s' unchanged" % options['id'])
