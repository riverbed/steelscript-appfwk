# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import logging

from django.core.management.base import BaseCommand
from steelscript.appfwk.apps.jobs.models import Job

from steelscript.common.datautils import Formatter

# not pretty, but pandas insists on warning about
# some deprecated behavior we really don't care about
# for this script, so ignore them all
import warnings
warnings.filterwarnings("ignore")


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'Work with already run jobs'

    def add_arguments(self, parser):
        group = parser.add_argument_group("Job Help",
                                          "Helper commands to manange jobs")
        group.add_argument('--list',
                           action='store_true',
                           dest='job_list',
                           default=False,
                           help='List all jobs')
        group.add_argument('--age',
                           action='store_true',
                           dest='job_age',
                           default=False,
                           help='Delete old/ancient jobs')
        group.add_argument('--flush',
                           action='store_true',
                           dest='job_flush',
                           default=False,
                           help='Delete all jobs without question')
        group.add_argument('--data',
                           action='store',
                           dest='job_data',
                           default=False,
                           help='Print data associated with a job')

        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file """
        self.stdout.write(msg, ending=ending)
        self.stdout.flush()

    def handle(self, *args, **options):
        """ Main command handler. """

        if options['job_list']:
            # print out the id's instead of processing anything
            columns = ['ID', 'Master', 'Parent', 'PID', 'Table', 'Created',
                       'Touched', 'Status', 'Refs', 'Progress', 'Data file']
            data = []
            for j in Job.objects.all().order_by('id'):

                datafile = os.path.basename(j.datafile())
                if not os.path.exists(j.datafile()):
                    datafile += " (missing)"

                status = (s for s in ('NEW', 'RUNNING', 'COMPLETE', 'ERROR')
                          if getattr(Job, s) == j.status).next()
                parent_id = j.parent.id if j.parent else '--'
                master_id = j.master.id if j.master else '--'

                data.append([j.id, master_id, parent_id, j.pid, j.table.name,
                             j.created, j.touched, status, j.refcount,
                             j.progress, datafile])

            Formatter.print_table(data, columns)

        elif options['job_data']:
            job = Job.objects.get(id=options['job_data'])

            columns = [c.name for c in job.table.get_columns()]

            if job.status == job.COMPLETE:
                Formatter.print_table(job.values(), columns)

        elif options['job_age']:
            logger.debug('Aging all jobs.')
            Job.objects.age_jobs(force=True)

        elif options['job_flush']:
            logger.debug('Flushing all jobs.')
            while Job.objects.count():
                ids = Job.objects.values_list('pk', flat=True)[:100]
                # Using list(ids) forces a DB hit, otherwise we may hit
                # a MySQL limitation
                Job.objects.filter(pk__in=list(ids)).delete()
