from django.conf import settings

#if settings.APPS_DATASOURCE['threading'] and not settings.TESTING:
#    from steelscript.appfwk.apps.jobs.task.async import AsyncTask
#    Task = AsyncTask
#else:
#    from steelscript.appfwk.apps.jobs.task.sync import SyncTask
#    Task = SyncTask

from steelscript.appfwk.apps.jobs.task.celerytask import CeleryTask
Task = CeleryTask
