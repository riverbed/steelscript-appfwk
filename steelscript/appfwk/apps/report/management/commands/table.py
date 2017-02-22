# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import sys
import time
import datetime
import logging

from django.core.management.base import BaseCommand

from steelscript.appfwk.apps.jobs.models import Job
from steelscript.appfwk.apps.datasource.models import Table
from steelscript.appfwk.apps.datasource.forms import TableFieldForm
from steelscript.appfwk.apps.report.models import Report, Widget
from steelscript.common.datautils import Formatter

# not pretty, but pandas insists on warning about
# some deprecated behavior we really don't care about
# for this script, so ignore them all
import warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'Run a defined table and return results in nice tabular format'

    def add_arguments(self, parser):
        group = parser.add_argument_group(
            title="Run Table Help",
            description="Helper commands to display list of tables to run"
        )

        group.add_argument('--table-list',
                           action='store_true',
                           dest='table_list',
                           default=False,
                           help='List all available tables by id')
        group.add_argument('--table-list-by-report',
                           action='store_true',
                           dest='table_list_by_report',
                           default=False,
                           help='List tables organized by report')

        group = parser.add_argument_group(
            "Run Table Criteria",
            "Options to specify criteria for specified run table.\n"
            "When adding time-based criteria, the timezone offset "
            "must be included, otherwise the time will be assumed as UTC.\n"
            "For example:\n"
            '"python manage.py table --table-id 19 -C endtime:9:01-0500"',
        )
        group.add_argument(
            '--table-id',
            action='store',
            dest='table_id',
            help='Table ID to execute (use --table-list to find the right ID)'
        )
        group.add_argument(
            '--table-name',
            action='store',
            dest='table_name',
            help='Table name to execute (use --table-list to list all tables)'
        )
        group.add_argument(
            '-C', '--criteria',
            action='append',
            type=str,
            dest='criteria',
            default=None,
            help='Specify criteria as <key>:<value>, repeat as necessary'
        )
        group.add_argument('--criteria-list',
                           action='store_true',
                           dest='criteria_list',
                           default=None,
                           help='List criteria for this table')

        group = parser.add_argument_group("Run Table Output Options",
                                          "Specify how data should be "
                                          "displayed")

        group.add_argument('-o', '--output-file',
                           dest='output_file',
                           default=None,
                           help='Output data to a file')
        group.add_argument('--csv',
                           action='store_true',
                           dest='as_csv',
                           default=False,
                           help='Output data in CSV format instead of tabular')
        group.add_argument('--columns',
                           action='store_true',
                           dest='only_columns',
                           default=False,
                           help='Output only columns ignoring data')
        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file. """
        if not self.options['as_csv']:
            self.stdout.write(msg, ending=ending)
            self.stdout.flush()

    def get_form(self, table, data=None):
        # First see if there's a single report associated with this table,
        # and if so, use it to get the field set
        widgets = Widget.objects.filter(tables__in=[table])
        sections = set()
        for w in widgets:
            sections.add(w.section)

        if len(sections) == 1:
            all_fields = widgets[0].collect_fields()
        else:
            all_fields = {}
            for f in table.fields.all():
                all_fields[f.keyword] = f

        return TableFieldForm(all_fields, use_widgets=False,
                              include_hidden=True, data=data)

    def handle(self, *args, **options):
        """ Main command handler. """
        self.options = options

        if options['table_list']:
            # print out the id's instead of processing anything
            output = []
            for t in Table.objects.all():
                output.append([t.id, t.namespace, t.queryclassname, t.name, t])
            Formatter.print_table(output, ['ID', 'Namespace', 'QueryClass',
                                           'Name', 'Table'])
        elif options['table_list_by_report']:
            # or print them out organized by report/widget/table
            output = []
            reports = Report.objects.all()
            for report in reports:
                for table in report.tables():
                    for widget in table.widget_set.all():
                        line = [table.id, report.title, widget.title, table]
                        output.append(line)
            Formatter.print_table(output, ['ID', 'Report', 'Widget', 'Table'])
        elif options['criteria_list']:
            if 'table_id' in options and options['table_id'] is not None:
                table = Table.objects.get(id=options['table_id'])
            elif 'table_name' in options and options['table_name'] is not None:
                table = Table.objects.get(name=options['table_name'])
            else:
                raise ValueError("Must specify either --table-id or "
                                 "--table-name to run a table")

            form = self.get_form(table)

            # Only show criteria options that were included in report
            # and given a label, other ones are for internal table use.
            # criteria like ignore_cache can still be passed in, they
            # just won't be shown in this list
            output = [(k, v.label)
                      for k, v in form.fields.iteritems() if v.label]
            Formatter.print_table(output, ['Keyword', 'Label'])
        else:
            if 'table_id' in options and options['table_id'] is not None:
                table = Table.objects.get(id=options['table_id'])
            elif 'table_name' in options and options['table_name'] is not None:
                table = Table.objects.get(name=options['table_name'])
            else:
                raise ValueError("Must specify either --table-id or "
                                 "--table-name to run a table")

            # Django gives us a nice error if we can't find the table
            self.console('Table %s found.' % table)

            # Parse criteria options
            criteria_options = {}
            if 'criteria' in options and options['criteria'] is not None:
                for s in options['criteria']:
                    (k, v) = s.split(':', 1)
                    criteria_options[k] = v

            form = self.get_form(table, data=criteria_options)

            if not form.is_valid(check_unknown=True):
                self.console('Invalid criteria:')
                logger.error('Invalid criteria: %s' %
                             ','.join('%s:%s' % (k, v)
                                      for k, v in form.errors.iteritems()))
                for k, v in form.errors.iteritems():
                    self.console('  %s: %s' % (k, ','.join(v)))

                sys.exit(1)

            criteria = form.criteria()

            columns = [c.name for c in table.get_columns()]

            if options['only_columns']:
                print columns
                return

            job = Job.create(table=table, criteria=criteria,
                             update_progress=False)
            job.save()

            self.console('Job created: %s' % job)
            self.console('Criteria: %s' % criteria.print_details())

            start_time = datetime.datetime.now()
            job.start()
            self.console('Job running . . ', ending='')

            # wait for results
            while not job.done():
                # self.console('. ', ending='')
                # self.stdout.flush()
                time.sleep(1)

            end_time = datetime.datetime.now()
            delta = end_time - start_time
            seconds = float(delta.microseconds +
                            (delta.seconds + delta.days*24*3600)*10**6)/10**6

            self.console('Done!! (elapsed time: %.2f seconds)' % seconds)
            self.console('')

            # Need to refresh the column list in case the job changed them
            # (ephemeral cols)
            columns = [c.name for c in table.get_columns()]

            if job.status == job.COMPLETE:
                if options['as_csv']:
                    if options['output_file']:
                        with open(options['output_file'], 'w') as f:
                            for line in Formatter.get_csv(job.values(),
                                                          columns):
                                f.write(line)
                                f.write('\n')
                    else:
                        Formatter.print_csv(job.values(), columns)
                else:
                    Formatter.print_table(job.values(), columns)
            else:
                self.console("Job completed with an error:")
                self.console(job.message)
                sys.exit(1)
