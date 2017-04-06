# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import sys
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from steelscript.common.datautils import Formatter
from steelscript.appfwk.apps.devices.models import Device

REQUIRED_DEVICE_ATTRS = ['host', 'module', 'name', 'username', 'password']
DEVICE_ATTRS = REQUIRED_DEVICE_ATTRS + ['enabled', 'port']


class Command(BaseCommand):
    args = ''
    help = 'Add, modify, delete and display device objects'

    def add_arguments(self, parser):
        parser.add_argument('--show',
                            action='store_true',
                            dest='show_device',
                            default=False,
                            help=('Show one or more matching device(s). '
                                  'For example:\n'
                                  './manage.py device --show --enabled'))

        parser.add_argument('--add',
                            action='store_true',
                            dest='add_device',
                            default=False,
                            help=('Add one device to the database. '
                                  'For example:\n'
                                  './manage.py device --add -H host -M module '
                                  '-N name -p port -U user -P password '
                                  '-E True'))

        parser.add_argument('--edit',
                            action='store_true',
                            dest='edit_device',
                            default=False,
                            help=('Edit one device identified by id. '
                                  'For example:\n'
                                  './manage.py device --edit -I 1 '
                                  '-N new_name'))

        parser.add_argument('--batch-file',
                            dest='batch_file',
                            help=("Batch file with info of multiple "
                                  "devices in the format of "
                                  "<name>,<module>,<hostname>,<port>,"
                                  "<username>,<password>,<AuthMethod>"
                                  "<access_code>,<tag1;tag2;...>"
                                  "for AuthMethod, 1 refers to "
                                  "username/password; 2 refers to OAuth2."
                                  ))

        parser.add_argument('--enabled', action='store_true', dest='enabled',
                            help='Set the device as enabled')
        parser.add_argument('--no-enabled', action='store_false',
                            dest='enabled', help='Set the device as disabled')

        parser.add_argument('-H', '--host', help='Hostname or IP address')
        parser.add_argument('-M', '--module',
                            help='Module name for the device')
        parser.add_argument('-N', '--name', help='Name of the device')
        parser.add_argument('-p', '--port',
                            help='Port of the device to connect')
        parser.add_argument('-U', '--username', help='Username for the device')
        parser.add_argument('-P', '--password', help='Password for the device')
        parser.add_argument('-I', '--id', help='ID of a device to be edited')

    def handle(self, *args, **options):
        """ Main command handler. """
        if options['show_device']:
            dev = {}
            for opt in DEVICE_ATTRS + ['id']:
                if options[opt] is not None:
                    dev[opt] = options[opt]

            output = []
            for d in Device.objects.filter(**dev):
                output.append([d.id, d.name, d.module, d.host, d.port,
                               d.username, d.enabled])
            Formatter.print_table(output, ['ID', 'Name', 'Module', 'Host',
                                           'Port', 'User Name', 'Enabled'])
            if not output:
                self.stdout.write("No device found")

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

            if options['enabled'] is not None:
                # --enabled or --no-enabled is set
                dev['enabled'] = options['enabled']

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

        elif options['batch_file']:
            file_name = options['batch_file']
            default_header = ['name', 'module', 'host', 'port',
                              'username', 'password', 'auth',
                              'access_code', 'tags']
            with open(file_name, 'r') as f:
                reader = csv.reader(f)
                devs = []
                add, update = 0, 0
                for i, row in enumerate(reader):
                    row = map(str.strip, row)
                    if i == 0:
                        if set(map(str.lower, row)) == set(default_header):
                            header = map(str.lower, row)
                            continue
                        else:
                            header = default_header

                    if not row or not row[0]:
                        continue

                    if len(row) < len(header):
                        msg = ('Line {0} only has {1} fields. '
                               '{2} fields are required.'
                               .format(i+1, len(row), len(header)))
                        raise CommandError(msg)

                    kwargs = dict(zip(header, row))

                    if not kwargs['host']:
                        msg = 'Host is empty string in line {0}.'.format(i+1)
                        raise CommandError(msg)

                    if not kwargs['port'].isdigit():
                        msg = ("Port should be integer instead of '{0}'"
                               " in line {1}".format(kwargs['port'], i+1))
                        raise CommandError(msg)

                    kwargs['port'] = int(kwargs['port'])
                    kwargs['enabled'] = True
                    kwargs['tags'] = ','.join(map(str.strip,
                                                  kwargs['tags'].split(';')))

                    # Check for device with same host and port
                    res = Device.objects.filter(host=kwargs['host'],
                                                port=kwargs['port'])
                    if res:
                        dev = res[0]
                        for k, v in kwargs.iteritems():
                            setattr(dev, k, v)
                        update += 1
                    else:
                        dev = Device(**kwargs)
                        add += 1

                    devs.append(dev)

                with transaction.atomic():
                    for dev in devs:
                        dev.save()

                self.stdout.write('{add} devices added. '
                                  '{update} existing devices refreshed.'
                                  .format(add=add, update=update))
