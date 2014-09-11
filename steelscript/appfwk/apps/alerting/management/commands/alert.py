# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
import optparse

from django.core.management.base import BaseCommand, CommandError

from steelscript.common.utils import Formatter
from steelscript.appfwk.apps.alerting.models import Alert


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = None
    help = 'View and manage system Alerts'

    def create_parser(self, prog_name, subcommand):
        """ Override super version to include special option grouping
        """
        parser = super(Command, self).create_parser(prog_name, subcommand)
        group = optparse.OptionGroup(parser, "Alert Help",
                                     "Helper commands to manange alerts")
        group.add_option('--list',
                         action='store_true',
                         dest='alert_list',
                         default=False,
                         help='List all alerts')
        group.add_option('--age',
                         action='store_true',
                         dest='alert_age',
                         default=False,
                         help='Delete old/ancient alerts according to settings')
        group.add_option('--flush',
                         action='store_true',
                         dest='alert_flush',
                         default=False,
                         help='Delete all alerts without question')
        group.add_option('--detail',
                         action='store',
                         dest='alert_detail',
                         default=False,
                         help='Print detailed information associated with an '
                              'alert ID')
        parser.add_option_group(group)

        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file """
        self.stdout.write(msg, ending=ending)
        self.stdout.flush()

    def handle(self, *args, **options):
        """ Main command handler. """

        if options['alert_list']:
            columns = ('ID', 'Timestamp', 'EventID', 'Level', 'Router',
                       'Destination', 'Message')
            data = []
            for a in Alert.objects.all().order_by('timestamp'):
                data.append((a.id, a.timestamp, a.eventid, a.level, a.router,
                             a.destination, a.message))
            Formatter.print_table(data, columns)

        elif options['alert_detail']:
            alert = Alert.objects.get(id=options['alert_detail'])
            self.stdout.write(alert.get_details())

        elif options['alert_age']:
            self.stdout.write('Not Implemented Yet')

        elif options['alert_flush']:
            logger.debug('Deleting all alerts.')
            Alert.objects.all().delete()

        else:
            raise CommandError('Missing appropriate option')
