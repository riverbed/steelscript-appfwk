# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import optparse

from django.core.management.base import BaseCommand
from django.core import management
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.plugins import plugins
from steelscript.appfwk.project.utils import Importer


class Command(BaseCommand):
    args = ''
    help = 'Reloads the configuration defined in the config directory'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report.'),

        optparse.make_option('--report-name',
                             action='store',
                             dest='report_name',
                             default=None,
                             help='Reload single report by fully qualified name.'),

        optparse.make_option('--report-dir',
                             action='store',
                             dest='report_dir',
                             default=None,
                             help='Reload reports from this directory.'),

        optparse.make_option('--namespace',
                             action='store',
                             dest='namespace',
                             default=None,
                             help='Reload reports under this namespace.'),

    )

    def import_module(self, module):

        #module = report.sourcefile
        report_name = module.split('.')[-1]
        try:
            self.importer.import_file(report_name, module)
        except ImportError as e:
            msg = ("Failed to import module '%s (%s)': %s"
                   % (report_name, module, str(e)))
            raise ImportError(msg)

    def capture_enabled(self, reports=None):
        if reports is None:
            reports = Report.objects.all()

        self.enabled_reports = dict()
        for r in reports:
            self.enabled_reports[(r.namespace, r.slug)] = r.enabled

    def apply_enabled(self):
        for (namespace, slug), enabled in self.enabled_reports.iteritems():
            try:
                report = Report.objects.get(namespace=namespace, slug=slug)
                report.enabled = enabled
                report.save()
            except ObjectDoesNotExist:
                pass

    def handle(self, *args, **options):
        self.stdout.write('Reloading report objects ... ')

        management.call_command('clean_pyc', path=settings.PROJECT_ROOT)

        self.importer = Importer(buf=self.stdout)

        if options['report_id']:
            # single report
            report_id = options['report_id']
            pk = int(report_id)
            report = Report.objects.get(pk=pk)

            management.call_command('clean',
                                    applications=False,
                                    report_id=report_id,
                                    clear_cache=False,
                                    clear_logs=False)

            DeviceManager.clear()
            self.import_module(report.sourcefile)

        elif options['report_name']:
            name = options['report_name']
            try:
                report = Report.objects.get(sourcefile__endswith=name)
                sourcefile = report.sourcefile
                management.call_command('clean',
                                        applications=False,
                                        report_id=report.id,
                                        clear_cache=False,
                                        clear_logs=False)
                self.import_module(sourcefile)
            except ObjectDoesNotExist:
                self.import_module(name)

            DeviceManager.clear()

        elif options['namespace']:
            reports = Report.objects.filter(namespace=options['namespace'])
            self.capture_enabled(reports)

            # clear all data from one namespace (module)
            for report in reports:
                management.call_command('clean',
                                        applications=False,
                                        report_id=report.id,
                                        clear_cache=False,
                                        clear_logs=False)

            # ignore all dirs besides the one we cleared, then import
            root_dir = settings.REPORTS_DIR
            target_dir = options['namespace']
            ignore_list = [os.path.basename(os.path.normpath(x))
                           for x in os.listdir(root_dir) if x != target_dir]
            self.importer.import_directory(
                root_dir, ignore_list=ignore_list)

            self.apply_enabled()

        else:
            self.capture_enabled()

            # clear all data
            management.call_command('clean',
                                    applications=True,
                                    report_id=None,
                                    clear_cache=True,
                                    clear_logs=False)

            # start with fresh device instances
            DeviceManager.clear()

            report_dir = settings.REPORTS_DIR
            self.importer.import_directory(report_dir, report_name=None)

            self.apply_enabled()
