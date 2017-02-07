# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.core.management.base import BaseCommand, CommandError

from steelscript.common.datautils import Formatter
from steelscript.appfwk.apps.alerting.models import Event, Alert


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'View and manage system Alerts and Events'

    def add_arguments(self, parser):
        group = parser.add_argument_group("Alert Help",
                                          "Helper commands to manange alerts")
        group.add_argument('--list-alerts',
                           action='store_true',
                           default=False,
                           help='List all alerts')
        group.add_argument('--list-events',
                           action='store_true',
                           default=False,
                           help='List all events')
        group.add_argument('--age',
                           action='store_true',
                           dest='alert_age',
                           default=False,
                           help='Delete old/ancient alerts based on settings')
        group.add_argument('--flush',
                           action='store_true',
                           dest='alert_flush',
                           default=False,
                           help='Delete all events and alerts without '
                                'question')
        group.add_argument('--alert-detail',
                           action='store',
                           default=False,
                           help='Print detailed information associated with '
                                'an alert ID')
        group.add_argument('--event-detail',
                           action='store',
                           default=False,
                           help='Print detailed information associated with '
                                'an event ID')

        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file """
        self.stdout.write(msg, ending=ending)
        self.stdout.flush()

    def handle(self, *args, **options):
        """ Main command handler. """

        if options['list_alerts']:
            columns = ('ID', 'Timestamp', 'EventID', 'Level', 'Sender',
                       'Dest Options', 'Message')
            data = []
            for a in Alert.objects.all().order_by('timestamp'):
                data.append((a.id, a.timestamp, a.event.eventid, a.level,
                             a.sender, a.options, a.message))
            Formatter.print_table(data, columns, padding=2)

        elif options['list_events']:
            columns = ('ID', 'Timestamp', 'EventID', '# Alerts', 'Context',
                       'Trigger Result')
            data = []
            for e in Event.objects.all().order_by('timestamp'):
                alert_count = len(e.alert_set.all())
                data.append((e.id, e.timestamp, e.eventid, alert_count,
                            str(e.context), str(e.trigger_result)[:30]))
            Formatter.print_table(data, columns, padding=2)

        elif options['alert_detail']:
            alert = Alert.objects.get(id=options['alert_detail'])
            self.stdout.write(alert.get_details())

        elif options['event_detail']:
            event = Event.objects.get(id=options['event_detail'])
            self.stdout.write(event.get_details())

        elif options['alert_age']:
            self.stdout.write('Not Implemented Yet')

        elif options['alert_flush']:
            logger.debug('Deleting all alerts.')
            Alert.objects.all().delete()

        else:
            raise CommandError('Missing appropriate option')
