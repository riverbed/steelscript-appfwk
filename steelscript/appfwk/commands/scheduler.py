#!/usr/bin/env python

import os
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

from django.core import management

from steelscript.commands.steel import (BaseCommand, shell,
                                        MainFailed, ShellFailed)


logger = logging.getLogger(__name__)
#call_command('table',
#      table_id=t.id,
#      as_csv=True,
#      output_file=filename,
#      criteria=['%s:%s' % (k, v) for (k, v) in criteria.iteritems()])


def run_table(*args, **kwargs):
    #management.call_command(*args, **kwargs)
    a = ' '.join(args)
    kws = ' '.join('--%s=%s' % (k, v) for k, v in kwargs.iteritems())
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
        parser.add_option('-l', '--list', help='List all running daemons')
        parser.add_option('-c', '--config', help='Config file to read schedule from')

    def get_settings(self):
        settings = os.path.join(os.getcwd(), 'local_settings.py')
        if os.path.exists(settings):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
            return settings
        else:
            raise MainFailed('Unable to find local_settings.py file')

    def add_job(self, name, job):
        #func = 'django.core.management:call_command'
        func = run_table
        args = 'table'

        # pull job kwargs from job dict
        keys = job.keys()
        job_kwargs = dict((k.lstrip('job_'), job.pop(k))
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

    def add_jobs(self):
        for s in self.parser.sections():
            job = dict(self.parser.items(s))
            self.add_job(s, job)

    def reload_config(self):
        logger.debug('Reloading job schedule configuration.')
        result = self.parser.read(self.options.config)
        if result is None:
            raise ValueError('No valid configuration loaded.')

        logger.debug('Clearing existing jobs.')
        for j in self.scheduler.get_jobs():
            self.scheduler.remove_job(j.id)

        self.add_jobs()

    def signal_handler(self, signum, frame):
        if signum == signal.SIGHUP:
            logger.info('Received signal %s, reloading config' % signum)
            self.reload_config()
        else:
            logger.info('Received signal %s, shutting down gracefully.' % signum)
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
