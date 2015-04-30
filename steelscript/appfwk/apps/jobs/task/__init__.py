from django.conf import settings

if (not hasattr(settings, 'APPFWK_TASK_MODEL')):
    raise Exception('settings.APPFWK_TASK_MODEL not set')

elif (settings.APPFWK_TASK_MODEL == 'sync') or settings.TESTING:
    from steelscript.appfwk.apps.jobs.task.sync import SyncTask
    Task = SyncTask

elif (settings.APPFWK_TASK_MODEL == 'async'):
    from steelscript.appfwk.apps.jobs.task.async import AsyncTask
    Task = AsyncTask

elif (settings.APPFWK_TASK_MODEL == 'celery'):
    from steelscript.appfwk.apps.jobs.task.celerytask import CeleryTask
    Task = CeleryTask

else:
    raise Exception('Unrecognized settings.APPFWK_TASK_MODEL: %s' %
                    settings.APPFWK_TASK_MODEL)
