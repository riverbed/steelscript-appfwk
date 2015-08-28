# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import optparse

from django.core.management.base import BaseCommand

from steelscript.appfwk.apps.report.utils import create_debug_zipfile


class Command(BaseCommand):
    args = ''
    help = 'Collects logfiles and system info and creates file `debug-<timestamp>.zip`'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--no-summary',
                             action='store_true',
                             dest='no_summary',
                             default=False,
                             help='Do not include summary created from steel about'),
    )

    def handle(self, *args, **options):
        fname = create_debug_zipfile(options['no_summary'])
        print 'Zipfile created: %s' % fname
