# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import shutil
import optparse
import pkg_resources

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from steelscript.appfwk.apps.plugins import plugins


class Command(BaseCommand):
    args = ''
    help = 'Collects reports into App Framework project.'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--overwrite',
                             action='store_true',
                             dest='overwrite',
                             default=False,
                             help='Overwrite ALL existing reports.'),
        optparse.make_option('--plugin',
                             action='store',
                             dest='plugin',
                             default=None,
                             help='Collect from specific report only. '
                                  'Use plugin.slug value, e.g. '
                                  '"netshark-datasource-plugin".'),
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
            open(os.path.join(dirname, '__init__.py'), 'w+').close()

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

        if options['plugin'] and options['plugin'] not in (p.slug for p in
                                                           plugins.enabled()):
            msg = (
                'Unable to find plugin: %s\n'
                'Check that the plugin is enabled and the plugin '
                'slug is spelled correctly.' % options['plugin']
            )
            raise CommandError(msg)

        for plugin in plugins.enabled():
            if options['plugin'] and plugin.slug != options['plugin']:
                continue

            reports = plugin.get_reports_paths()
            if reports:
                rdir = os.path.join(report_dir, plugin.get_namespace())
                self.ensure_dir(rdir)

                for name, src_file in reports:
                    dest_file = os.path.join(rdir, name + '.py')
                    self.copyfile(src_file, dest_file, options['overwrite'])
