import celery
import logging

from steelscript.appfwk.apps.jobs.task.base import BaseTask

logger = logging.getLogger(__name__)


class CeleryTask(BaseTask):

    def __unicode__(self):
        return "<CeleryTask %s>" % (self.job)

    def __str__(self):
        return "<CeleryTask %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def start(self):
        task_start.delay(self)


@celery.task()
def task_start(task):
    task.call_method()


@celery.task()
def task_results_callback(results, task):
    task.call_method()
