import logging
import threading
import sys

from steelscript.appfwk.apps.jobs.task.base import BaseTask

logger = logging.getLogger(__name__)


class AsyncTask(threading.Thread, BaseTask):
    def __init__(self, job, queryclass):
        threading.Thread.__init__(self)
        self.daemon = True
        self.job = job
        self.queryclass = queryclass

        logger.info("%s created" % self)

    def __delete__(self):
        if self.job:
            self.job.dereference("AsyncTask deleted")

    def __unicode__(self):
        return "<AsyncTask %s>" % (self.job)

    def __str__(self):
        return "<AsyncTask %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def run(self):
        self.do_run()
        sys.exit(0)
