# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import shutil
import optparse
import pkg_resources

from django.core.management.base import BaseCommand
from django.conf import settings

from steelscript.appfwk.apps.plugins import plugins


class Command(BaseCommand):
    args = None
    help = 'Collects reports into App Framework project.'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--overwrite',
                             action='store_true',
                             dest='overwrite',
                             default=False,
                             help='Overwrite ALL existing reports.'),
    )

    def copyfile(self, src, dest, overwrite=False):
        if os.path.exists(dest) and not overwrite:
            if self.verbose:
                self.stdout.write(' skipping %s\n' % dest)
            return

        if self.verbose:
            self.stdout.write(' copying %s --> %s\n' % (src, dest))
        shutil.copy2(src, dest)

    def ensure_dir(self, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)
            open(os.path.join(dirname, '__init__.py'), 'wa').close()

    def handle(self, *args, **options):
        self.verbose = int(options['verbosity']) > 1

        report_dir = settings.REPORTS_DIR
        self.ensure_dir(report_dir)

        self.stdout.write('Collecting reports to %s ... \n' % report_dir)

        # copy default reports
        src_dir = pkg_resources.resource_filename('steelscript.appfwk.apps',
                                                  '../reports')
        for f in os.listdir(src_dir):
            if f.startswith('__init__') or not f.endswith('.py'):
                continue

            src_file = os.path.join(src_dir, f)
            dest_file = os.path.join(report_dir, f)
            self.copyfile(src_file, dest_file, options['overwrite'])

        for plugin in plugins.enabled():
            reports = plugin.get_reports_paths()
            if reports:
                rdir = os.path.join(report_dir, plugin.get_namespace())
                self.ensure_dir(rdir)

                for name, src_file in reports:
                    dest_file = os.path.join(rdir, name + '.py')
                    self.copyfile(src_file, dest_file, options['overwrite'])
