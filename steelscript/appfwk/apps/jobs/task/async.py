# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys
import logging
import threading

from steelscript.appfwk.apps.jobs.task.base import BaseTask

logger = logging.getLogger(__name__)


def validate(job):
    # check if incomplete jobs are still running by sending
    # a harmless signal 0 to that PID
    # or if jobs were never started and even given a PID
    def pid_active(pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    if not job.done():
        if job.pid is None or not pid_active(job.pid):
            return False

    return True


class AsyncTask(threading.Thread, BaseTask):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        BaseTask.__init__(self, *args, **kwargs)
        self.daemon = True

    def __delete__(self):
        if self.job:
            self.job.dereference("AsyncTask deleted")

    def __unicode__(self):
        return "<AsyncTask %s>" % (self.job)

    def __str__(self):
        return "<AsyncTask %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    @classmethod
    def validate_jobs(cls, jobs, delete=False):
        valid_jobs = []
        for j in jobs:
            if validate(j):
                valid_jobs.append(j)
            elif delete:
                logging.debug('Deleting stale job %s with PID %s' % (j, j.pid))
                j.delete()
            else:
                logging.debug('Ignoring stale job %s with PID %s' % (j, j.pid))

        return valid_jobs

    def run(self):
        self.call_method()
        sys.exit(0)
