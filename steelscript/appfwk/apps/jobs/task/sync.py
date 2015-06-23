import logging

from steelscript.appfwk.apps.jobs.task.base import BaseTask

logger = logging.getLogger(__name__)


class SyncTask(BaseTask):
    def start(self):
        self.call_method()
