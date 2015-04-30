import celery
import logging

from steelscript.appfwk.apps.jobs.task.base import BaseTask

logger = logging.getLogger(__name__)


class CeleryTask(BaseTask):

    def start(self):
        task_start.delay(self)


@celery.task()
def task_start(task):
    task.call_method()


@celery.task()
def task_results_callback(results, task):
    task.call_method()
