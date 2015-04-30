import logging
import threading
import sys

from steelscript.appfwk.apps.jobs.task.base import BaseTask

logger = logging.getLogger(__name__)


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

    def run(self):
        self.call_method()
        sys.exit(0)
