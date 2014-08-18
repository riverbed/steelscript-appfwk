#!/usr/bin/env python

"""
scheduler.py

Command script to run schduled table jobs according to
defined configuration.

The config file uses the ConfigParser format. For example:

    [job1]
    table-name=pypi-download-stats-alerts
    criteria=duration:1day, package:steelscript
    output-file=statsalerts.csv
    csv=
    job_trigger=interval
    job_seconds=10

    [job2]
    table-name=appfwk-alerts
    criteria=duration:1hour
    job_trigger=interval
    job_seconds=15

Each section name (the line with sourrounding brackets) will
translate into a scheduled job name.  The key-value pairs include
parameters for the table command itself (e.g. 'table-name', 'criteria'),
and job configuration that gets handled by the scheduler
(e.g. 'job_trigger', 'job_seconds').  Note that job configuration
keys are all prefixed with 'job_'.

"""

import os
import re
import sys
import signal
import logging
from ConfigParser import SafeConfigParser

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
except ImportError:
    print 'This module requires an additional python module'
    print 'called "apschduler", ensure this is installed and try again'
    sys.exit(1)

from steelscript.commands.steel import (BaseCommand, shell, console,
                                        MainFailed, ShellFailed)


logger = logging.getLogger(__name__)


def run_table(*args, **kwargs):
    #management.call_command(*args, **kwargs)

    # combine base arguments
    a = ' '.join(args)

    # if we have criteria, parse and append to base
    criteria = kwargs.pop('criteria', None)
    if criteria:
        crits = re.split(',\s|,|\s', criteria)
        critargs = ' '.join(['--criteria=%s' % c for c in crits])
        a = '%s %s' % (a, critargs)

    # format remaining keyword args
    kws = []
    for k, v in kwargs.iteritems():
        if v in ('True', ''):
            # handle empty or True attrs as command-line flags
            kws.append('--%s' % k)
        else:
            kws.append('--%s=%s' % (k, v))

    kws = ' '.join(kws)

    cmd = 'python manage.py %s %s' % (a, kws)
    logger.debug('running command: %s' % cmd)

    try:
        results = shell(cmd, cwd=os.getcwd(), save_output=True,
                        allow_fail=False, exit_on_fail=False, log_output=False)
    except ShellFailed as e:
        logger.error('Error processing table.  Error code: %s, '
                     'stdout results: %s' % (e.returncode, e.output))


class Command(BaseCommand):
    help = 'Interface to schedule table operations.'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        # XXX SIGHUP not available on windows
        signal.signal(signal.SIGHUP, self.signal_handler)
        # graceful shutdown on Ctrl-C
        signal.signal(signal.SIGINT, self.signal_handler)

    def add_options(self, parser):
        super(Command, self).add_options(parser)
        parser.add_option('-c', '--config',
                          help='Config file to read schedule from')

    def get_settings(self):
        settings = os.path.join(os.getcwd(), 'local_settings.py')
        if os.path.exists(settings):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
            return settings
        else:
            raise MainFailed('Unable to find local_settings.py file')

    def schedule_job(self, name, job):
        #func = 'django.core.management:call_command'
        func = run_table
        args = 'table'

        # pull job kwargs from job dict
        keys = job.keys()
        job_kwargs = dict((k[4:], job.pop(k))
                          for k in keys if k.startswith('job_'))

        # hardcode the function call - don't allow config overrides
        job_kwargs['name'] = name
        job_kwargs['func'] = func
        job_kwargs['args'] = [args]

        # add remaining kwargs as actual kwargs for function call
        #job['settings'] = self.get_settings()
        job_kwargs['kwargs'] = job

        # convert time fields to floats
        for v in ['weeks', 'days', 'hours', 'minutes', 'seconds']:
            if v in job_kwargs:
                job_kwargs[v] = float(job_kwargs[v])

        logger.debug('Scheduling job with kwargs: %s' % job_kwargs)
        self.scheduler.add_job(**job_kwargs)

    def schedule_jobs(self):
        for s in self.parser.sections():
            job = dict(self.parser.items(s))
            self.schedule_job(s, job)

    def reload_config(self):
        logger.debug('Reloading job schedule configuration.')
        result = self.parser.read(self.options.config)
        if result is None:
            raise ValueError('No valid configuration loaded.')

        logger.debug('Clearing existing jobs.')
        for j in self.scheduler.get_jobs():
            self.scheduler.remove_job(j.id)

        self.schedule_jobs()

    def signal_handler(self, signum, frame):
        if signum == signal.SIGHUP:
            console('Received signal %s, reloading config' % signum)
            self.reload_config()
        else:
            console('Received signal %s, shutting down gracefully.' % signum)
            if self.scheduler.running:
                self.scheduler.shutdown()
            sys.exit()

    def main(self):
        self.scheduler = BlockingScheduler()
        self.parser = SafeConfigParser()

        if not self.options.config:
            raise MainFailed('Config file required')

        self.reload_config()

        logger.debug('Starting scheduler.')
        self.scheduler.start()
