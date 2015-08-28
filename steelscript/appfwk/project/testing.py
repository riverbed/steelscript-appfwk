# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import sys
import signal
import logging
import subprocess

import pkg_resources
from django.test.runner import DiscoverRunner


logger = logging.getLogger(__name__)


def start_progressd():
    print 'Starting progressd ...'
    logger.info('Starting progressd ...')
    pdpath = pkg_resources.get_distribution('steelscript.appfwk').location
    pd = os.path.join(pdpath, 'steelscript', 'appfwk',
                      'progressd', 'progressd.py')
    pid = subprocess.Popen([sys.executable, pd,
                            '--no-sync-jobs', '--port', '5555']).pid
    with open('/tmp/test-progressd.pid', 'w') as f:
        f.write(str(pid) + '\n')


def stop_progressd():
    print 'Stopping progressd ...'
    logger.info('Stopping progressd ...')
    try:
        with open('/tmp/test-progressd.pid', 'r') as f:
            pid = f.read().splitlines()[0]
    except IOError:
        logger.error('Error: progressd not running')
        return

    try:
        os.kill(int(pid), signal.SIGTERM)
    except OSError as e:
        logger.error('Error stopping progressd: %s' % e)

    os.unlink('/tmp/test-progressd.pid')


class AppfwkTestRunner(DiscoverRunner):
    """Custom Test Runner which starts/stops progressd."""

    def setup_test_environment(self, **kwargs):
        super(AppfwkTestRunner, self).setup_test_environment(**kwargs)
        start_progressd()

    def teardown_test_environment(self, **kwargs):
        super(AppfwkTestRunner, self).teardown_test_environment(**kwargs)
        stop_progressd()


class CeleryAppfwkTestRunner(AppfwkTestRunner):
    """Custom Test Runner which starts/stops progressd and uses Celery."""

    def setup_test_environment(self, **kwargs):
        from djcelery.contrib.test_runner import _set_eager
        _set_eager()
        super(CeleryAppfwkTestRunner, self).setup_test_environment(**kwargs)


class JenkinsAppfwkTestRunner(AppfwkTestRunner):
    """Add support for JUXD-style output for Jenkins builds."""

    def run_suite(self, suite, **kwargs):
        from juxd import JUXDTestRunner
        return JUXDTestRunner(verbosity=self.verbosity,
                              failfast=self.failfast).run(suite)
