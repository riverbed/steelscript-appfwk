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
    interval_seconds=10

    [job2]
    ; comments are prefixed by a semi-colon
    table-name=appfwk-alerts
    criteria=duration:1hour
    interval_seconds=15

    [job3]
    table-name=appfwk-alerts
    ; you can interpolate other values via keywords
    criteria=duration:%(interval_minutes)sminutes
    interval_seconds=0
    interval_minutes=15

    [job4]
    table-name=appfwk-alerts
    criteria=duration:%(interval_minutes)sminutes
    interval_seconds=0
    interval_minutes=15
    ; offsets can be used to run reports further in the past
    offset=1min

Each section name (the line with sourrounding brackets) will
translate into a scheduled job name.  The key-value pairs include
parameters for the table command itself (e.g. 'table-name', 'criteria'),
and job configuration that gets handled by the scheduler
(e.g. 'interval_trigger', 'interval_seconds').  Note that job configuration
keys are all prefixed with 'interval_'.

"""

import os
import re
import sys
import signal
import logging
import datetime
from collections import namedtuple
from ConfigParser import SafeConfigParser

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
except ImportError:
    print 'This module requires an additional python module'
    print 'called "apscheduler", ensure this is installed and try again'
    sys.exit(1)

import pytz

from steelscript.common import timeutils
from steelscript.commands.steel import (BaseCommand, shell, console,
                                        MainFailed, ShellFailed)


logger = logging.getLogger(__name__)


def run_table(*args, **kwargs):
    #management.call_command(*args, **kwargs)

    # get runtime parameters
    interval = kwargs.pop('interval')

    if interval['offset'] > datetime.timedelta(0):
        # round now to nearest whole second
        now = datetime.datetime.now(pytz.UTC)
        roundnow = timeutils.round_time(now, round_to=1)

        endtime = roundnow - interval['offset']
    else:
        endtime = None


    # combine base arguments
    argstr = ' '.join(args)

    # if we have criteria, parse and append to base
    criteria = kwargs.pop('criteria', None)
    critargs = ''
    if criteria:
        crits = re.split(',\s|,|\s', criteria)
        critargs = ' '.join(['--criteria=%s' % c for c in crits])
        argstr = '%s %s' % (argstr, critargs)

        if endtime:
            endstr = '--criteria=endtime:"%s"' % str(endtime)
            argstr = '%s %s' % (argstr, endstr)

            logger.debug('Setting end time to %s (via offset: %s)' %
                         (endstr, interval['offset']))

    # format remaining keyword args
    kws = []
    for k, v in kwargs.iteritems():
        if v.lower() in ('true', ''):
            # handle empty or True attrs as command-line flags
            kws.append('--%s' % k)
        else:
            kws.append('--%s=%s' % (k, v))

    kws = ' '.join(kws)

    cmd = 'python manage.py %s %s' % (argstr, kws)
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
        # holdover for direct python call
        settings = os.path.join(os.getcwd(), 'local_settings.py')
        if os.path.exists(settings):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
            return settings
        else:
            raise MainFailed('Unable to find local_settings.py file')

    def get_job_function(self):
        # allow for alternate methods to call table commands in future
        # possibly direct API calls, or REST calls against running server
        #func = 'django.core.management:call_command'

        job_params = {'func': run_table,
                      'args': ['table']}
        return job_params

    def parse_config(self, job_config):
        """Breaks up dict from config section into job and function options.

        Returns new dict suitable for passing to add_job, plus dict
        of interval definitions.
        """
        # pull job scheduler kwargs from job_config dict
        interval = dict()
        offset = timeutils.parse_timedelta(job_config.pop('offset', '0'))

        keys = job_config.keys()
        job_kwargs = dict((k[9:], job_config.pop(k))
                          for k in keys if k.startswith('interval_'))

        # convert time fields to floats, populate interval dict
        for v in ['weeks', 'days', 'hours', 'minutes', 'seconds']:
            if v in job_kwargs:
                val = float(job_kwargs[v])
                job_kwargs[v] = val
                interval[v] = val
        interval['delta'] = datetime.timedelta(**interval)
        interval['offset'] = offset

        # hardcode the function call - don't allow config overrides
        job_kwargs.update(self.get_job_function())

        # add remaining kwargs as actual kwargs for function call
        job_config['interval'] = interval
        job_kwargs['kwargs'] = job_config

        return job_kwargs, interval

    def schedule_job(self, name, job_config):
        job_options, interval = self.parse_config(job_config)

        if interval['offset'] > datetime.timedelta(0):
            delta = timeutils.timedelta_total_seconds(interval['delta'])
            offset = timeutils.timedelta_total_seconds(interval['offset'])
            now = datetime.datetime.now(pytz.UTC)
            next_run_time = timeutils.round_time(now,
                                                 round_to=delta + offset,
                                                 round_up=True)
            logger.debug('Setting next run time to %s (delta: %d, offset: %d)' %
                         (next_run_time, delta, offset))
            job_options['next_run_time'] = next_run_time

        logger.debug('Scheduling job named %s with kwargs: %s' % (name,
                                                                  job_options))
        self.scheduler.add_job(name=name, trigger='interval', **job_options)

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
