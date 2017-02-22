# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import glob
import optparse

from django.apps import apps
from django.core.management.base import BaseCommand
from django.core import management
from django.db import connection
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist

from django.conf import settings
from steelscript.appfwk.apps.jobs.models import Job
from steelscript.appfwk.apps.report.models import Report, WidgetJob
from steelscript.appfwk.apps.datasource.models import (Table, TableField,
                                                       Column)
from steelscript.appfwk.apps.alerting.models import (Destination, TriggerCache,
                                                     ErrorHandlerCache)


class Command(BaseCommand):
    args = ''
    help = 'Clears existing data caches, logs, and application settings.'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--applications',
                             action='store_true',
                             dest='applications',
                             default=False,
                             help='Reset all application configurations.'),
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report instead of all apps.'),
        optparse.make_option('--clear-cache',
                             action='store_true',
                             dest='clear_cache',
                             default=False,
                             help='Clean datacache files.'),
        optparse.make_option('--clear-logs',
                             action='store_true',
                             dest='clear_logs',
                             default=False,
                             help='Delete logs and debug files.'),
    )

    def handle(self, *args, **options):
        db_exists = Job._meta.db_table in connection.introspection.table_names()

        if options['clear_cache']:
            # first delete all jobs
            self.stdout.write('Clearing all jobs ... ', ending='')
            if db_exists:
                Job.objects.all().delete()
            self.stdout.write('done.')

            # now clear any remaining cache files
            self.stdout.write('Removing cache files ... ', ending='')
            for f in os.listdir(settings.DATA_CACHE):
                if f != '.gitignore':
                    try:
                        os.unlink(os.path.join(settings.DATA_CACHE, f))
                    except OSError:
                        pass
            self.stdout.write('done.')

        if options['clear_logs']:
            self.stdout.write('Removing debug files ... ', ending='')
            for f in glob.glob(os.path.join(settings.PROJECT_ROOT,
                                            'debug-*.zip')):
                os.remove(f)
            self.stdout.write('done.')

            self.stdout.write('Removing log files ... ', ending='')
            # delete rolled over logs
            for f in glob.glob(os.path.join(settings.PROJECT_ROOT,
                                            'log*.txt.[1-9]')):
                os.remove(f)
            # truncate existing logs
            for f in glob.glob(os.path.join(settings.PROJECT_ROOT,
                                            'log*.txt')):
                with open(f, 'w'):
                    pass
            self.stdout.write('done.')

        if options['applications']:
            # reset objects from main applications
            apps_to_clean = ['report', 'datasource', 'alerting']
            for app in apps_to_clean:
                for model in apps.get_app_config(app).get_models():
                    if model.__name__ not in ['Alert', 'WidgetAuthToken']:
                        # Avoid deleting Alerts when running a basic clean
                        self.stdout.write('Deleting objects from %s\n' % model)
                        model.objects.all().delete()

        elif options['report_id']:
            # remove Report and its Widgets, Jobs, WidgetJobs, Tables, Columns
            rid = options['report_id']

            def del_table(tbl):
                related_tables = ((tbl.options or {}).get('related_tables'))
                for ref in (related_tables or {}).values():
                    try:
                        del_table(Table.from_ref(ref))
                    except ObjectDoesNotExist:
                        # already deleted
                        pass

                Column.objects.filter(table=tbl.id).delete()
                Job.objects.filter(table=tbl.id).delete()

                for trigger in TriggerCache.filter(tbl):
                    trigger.delete()

                for handler in ErrorHandlerCache.filter(tbl):
                    handler.delete()

                # delete newly unreferenced routes
                Destination.objects.filter(trigger=None).delete()

                tables = (tbl.options or {}).get('tables')
                for ref in (tables or {}).values():
                    try:
                        del_table(Table.from_ref(ref))
                    except ObjectDoesNotExist:
                        # already deleted
                        pass

                tbl.delete()

            for section in Report.objects.get(id=rid).section_set.all():
                for widget in section.widget_set.all():
                    for table in widget.tables.all():
                        del_table(table)
                        for wjob in WidgetJob.objects.filter(widget=widget):
                            wjob.delete()
                    widget.delete()

            # Delete TableFields no longer referenced by any Tables or Sections
            (TableField.objects
             .annotate(reports=Count('report'),
                       sections=Count('section'),
                       tables=Count('table'))
             .filter(reports=0, sections=0, tables=0)
             .delete())

            report = Report.objects.get(id=rid)

            report.delete()

        # clear model caches
        TriggerCache.clear()
        ErrorHandlerCache.clear()

        # rotate the logs once
        management.call_command('rotate_logs')
