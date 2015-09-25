# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import celery
import logging
import djcelery
from celery.signals import worker_ready, worker_shutdown

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


class CeleryInspector(object):
    _workers = None
    _needs_update = True

    queues = ('active', 'scheduled', 'reserved')

    def flag_update(self):
        self._needs_update = True

    def update_workers(self):
        """Update internal worker list if needed."""
        if self._needs_update:
            w = djcelery.celery.control.inspect().active_queues()
            if w:
                self._workers = w.keys()
                logging.debug('Updated workers are: %s' % (self._workers))
            else:
                logging.warning('No active queues found.')

            self._needs_update = False

    def get_queue(self, queue):
        i = djcelery.celery.control.inspect(self._workers)
        queues = getattr(i, queue)()

        # each worker reports a list of jobs, untangle into single list
        jobs = []
        for worker in queues.values():
            for job in worker:
                # add args from active and scheduled queues
                if 'args' in job:
                    jobs.append(job['args'])
                elif 'request' in job:
                    jobs.append(job['request']['args'])
        return jobs

    def get_all_queues(self):
        self.update_workers()

        jobs = []
        for q in self.queues:
            jobs.extend(self.get_queue(q))
        return jobs

    def check_job(self, job):
        self.update_workers()

        for q in self.queues:
            for j in self.get_queue(q):
                if str(job) in j:
                    logging.debug('Found alive job %s in queue %s' % (j, q))
                    return True
        return False


inspector = CeleryInspector()


def update_inspector(signal=None, sender=None, **kwargs):
    logging.debug('Received signal %s, from sender %s' %
                  (signal, sender))
    inspector.flag_update()

worker_ready.connect(update_inspector)
worker_shutdown.connect(update_inspector)
