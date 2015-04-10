import os
import sys
import time
import random
import hashlib
import logging
import datetime
import importlib
import traceback
import threading
import celery
#from celery.contrib.methods import task

import pytz
import pandas
import numpy
from django.db import models
from django.db import transaction
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings

from steelscript.appfwk.libs.fields import \
    Callable, CallableField

from steelscript.appfwk.apps.datasource.models import Table

from steelscript.appfwk.apps.datasource.exceptions import DataError
from steelscript.appfwk.apps.alerting.models import (post_data_save,
                                                     error_signal)
from steelscript.appfwk.libs.fields import PickledObjectField


logger = logging.getLogger(__name__)


if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):
    # sqlite doesn't support row locking (select_for_update()), so need
    # to use a threading lock.  This provides support when running
    # the dev server.  It will not work across multiple processes, only
    # between threads of a single process
    lock = threading.RLock()
else:
    lock = None

age_jobs_last_run = 0


class LocalLock(object):
    def __enter__(self):
        if lock is not None:
            lock.acquire()

    def __exit__(self, type_, value, traceback_):
        if lock is not None:
            lock.release()
        return False


class QueryResponse(object):

    QUERY_COMPLETE = 1
    QUERY_CONTINUE = 2
    QUERY_ERROR = 3

    def __init__(self, status):
        self.status = status

    def is_complete(self):
        return self.status == QueryResponse.QUERY_COMPLETE

    def is_error(self):
        return self.status == QueryResponse.QUERY_ERROR


class QueryComplete(QueryResponse):

    def __init__(self, data):
        super(QueryComplete, self).__init__(QueryResponse.QUERY_COMPLETE)
        self.data = data


class QueryContinue(QueryResponse):

    def __init__(self, callback, jobs=None):
        super(QueryContinue, self).__init__(QueryResponse.QUERY_CONTINUE)
        self.callback = callback
        self.jobs = jobs


class QueryError(QueryResponse):
    def __init__(self, message=None):
        super(QueryError, self).__init__(QueryResponse.QUERY_ERROR)
        self.message = message


class Job(models.Model):

    # Timestamp when the job was created
    created = models.DateTimeField(auto_now_add=True)

    # Timestamp the last time the job was accessed
    touched = models.DateTimeField(auto_now_add=True)

    # Number of references to this job
    refcount = models.IntegerField(default=0)

    # Parent job that spawned this job (and thus waiting for
    # this jobs results)
    parent = models.ForeignKey('self', null=True, related_name='children')

    # Master job that has run (or is running) that has the same
    # criteria.  If master, this job is a "follower"
    master = models.ForeignKey('self', null=True, related_name='followers')

    # Table associated with this job
    table = models.ForeignKey(Table)

    # Criteria used to start this job - an instance of the Criteria class
    criteria = PickledObjectField(null=True)

    # Actual criteria as returned by the job after running
    actual_criteria = PickledObjectField(null=True)

    # Unique handle for the job
    handle = models.CharField(max_length=100, default="")

    # Job status
    NEW = 0
    RUNNING = 1
    COMPLETE = 3
    ERROR = 4

    status = models.IntegerField(
        default=NEW,
        choices=((NEW, "New"),
                 (RUNNING, "Running"),
                 (COMPLETE, "Complete"),
                 (ERROR, "Error")))

    # Message if job complete or error
    message = models.TextField(default="")

    # If an error comes from a Python exception, this will contain the full
    # exception text with traceback.
    exception = models.TextField(default="")

    # Whether to update detailed progress
    update_progress = models.BooleanField(default=True)

    # While RUNNING, this provides an indicator of progress 0-100
    progress = models.IntegerField(default=-1)

    # While RUNNING, time remaining
    remaining = models.IntegerField(default=None, null=True)

    #
    callback = CallableField()

    def __unicode__(self):
        return "<Job %s (%8.8s) - t%s>" % (self.id, self.handle, self.table.id)

    def __repr__(self):
        return unicode(self)

    def refresh(self):
        """ Refresh dynamic job parameters from the database. """
        # fix bug 227119, by avoiding mysql caching problems
        # http://stackoverflow.com/a/7028362
        # should be fixed in Django 1.6
        Job.objects.update()
        job = Job.objects.get(pk=self.pk)
        for k in ['status', 'message', 'exception', 'progress', 'remaining',
                  'actual_criteria', 'touched', 'refcount', 'callback', 'parent']:
            setattr(self, k, getattr(job, k))

    @property
    def is_child(self):
        return self.parent is not None

    @property
    def is_follower(self):
        return self.master is not None

    def safe_update(self, **kwargs):
        """ Update the job with the passed dictionary in a database safe way.

        This method updates only the requested paraemters and refreshes
        the rest from the database.  This should be used for all updates
        to Job's to ensure that unmodified keys are not accidentally
        clobbered by doing a blanket job.save().

        """

        if kwargs is None:
            return

        logger.debug("%s safe_update %s" % (self, kwargs))
        Job.objects.filter(pk=self.pk).update(**kwargs)
        self.refresh()

        if not self.is_follower:
            # Push changes to children of this job
            child_kwargs = {}
            for k, v in kwargs.iteritems():
                if k in ['status', 'message', 'exception', 'progress',
                         'remaining', 'actual_criteria']:
                    child_kwargs[k] = v
            # There should be no recursion, so a direct update to the
            # database is possible.  (If recursion, would need to call
            # self_update() on each child.)
            Job.objects.filter(master=self).update(**child_kwargs)

    @classmethod
    def create(cls, table, criteria, update_progress=True, parent=None):

        with LocalLock():
            with transaction.atomic():
                # Grab a lock on the row associated with the table
                table = Table.objects.select_for_update().get(id=table.id)

                criteria = criteria.build_for_table(table)
                # Lockdown start/endtimes
                try:
                    criteria.compute_times()
                except ValueError:
                    # Ignore errors, this table may not have start/end times
                    pass

                # Compute the handle -- this will take into account
                # cacheability
                handle = Job._compute_handle(table, criteria)

                # Look for another job by the same handle in any state
                # except ERROR
                if not criteria.ignore_cache:
                    masters = (Job.objects
                               .select_for_update()
                               .filter(status__in=[Job.NEW,
                                                   Job.COMPLETE,
                                                   Job.RUNNING],
                                       handle=handle,
                                       master=None)
                               .order_by('created'))
                else:
                    masters = None

                if masters is not None and len(masters) > 0:
                    master = masters[0]

                    job = Job(table=table,
                              criteria=criteria,
                              actual_criteria=master.actual_criteria,
                              status=master.status,
                              handle=handle,
                              master=master,
                              parent=parent,
                              update_progress=master.update_progress,
                              progress=master.progress,
                              remaining=master.remaining,
                              message='',
                              exception='')
                    job.save()

                    master.reference("Master link from job %s" % job)
                    now = datetime.datetime.now(tz=pytz.utc)
                    master.safe_update(touched=now)

                    logger.info("%s: New job for table %s, linked to master %s"
                                % (job, table.name, master))
                else:
                    job = Job(table=table,
                              criteria=criteria,
                              status=Job.NEW,
                              handle=handle,
                              parent=parent,
                              master=None,
                              update_progress=update_progress,
                              progress=0,
                              remaining=-1,
                              message='',
                              exception='')
                    job.save()
                    logger.info("%s: New job for table %s" % (job, table.name))

                logger.debug("%s: criteria = %s" % (job, criteria))

            # Flush old jobs
            Job.age_jobs()

        return job

    def delayed_progress(self, p):
        print "%s: status %s (on enter)" % (p, self.get_status_display())
        with transaction.atomic():
            Job.objects.select_for_update().get(id=self.id)
            print "%s: status %s (after select)" % (p, self.get_status_display())
            self.refresh()
            #print "%s: status %s (refreshed)" % (p, self.get_status_display())
            if self.status != self.COMPLETE:
                self.status = self.COMPLETE
                self.progress = p
                self.save()
                print "%s: updated to COMPLETE" % (p)
            else:
                print "%s: skipping, status already DONE" % (p)

            time.sleep(5)

        self.refresh()
        print "%s: status %s, progress %s" % (p, self.get_status_display(), self.progress)

    @classmethod
    def _compute_handle(cls, table, criteria):
        h = hashlib.md5()
        h.update(str(table.id))

        if table.cacheable and not criteria.ignore_cache:
            # XXXCJ - Drop ephemeral columns when computing the cache handle,
            # since the list of columns is modifed at run time.   Typical use
            # case is an analysis table which creates a time-series graph of
            # the top 10 hosts -- one column per host.  The host columns will
            # change based on the run of the dependent table.
            #
            # Including epheremal columns causes some problems because the
            # handle is computed before the query is actually run, so it never
            # matches.
            #
            # May want to dig in to this further and make sure this doesn't
            # pick up cache files when we don't want it to
            h.update('.'.join([c.name for c in
                               table.get_columns()]))

            if table.criteria_handle_func:
                criteria = table.criteria_handle_func(criteria)

            for k, v in criteria.iteritems():
                # logger.debug("Updating hash from %s -> %s" % (k,v))
                h.update('%s:%s' % (k, v))
        else:
            # Table is not cacheable, instead use current time plus a random
            # value just to get a unique hash
            h.update(str(datetime.datetime.now()))
            h.update(str(random.randint(0, 10000000)))

        return h.hexdigest()

    def reference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount') + 1)
        # logger.debug("%s: reference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def dereference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount') - 1)
        # logger.debug("%s: dereference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def get_columns(self, ephemeral=None, **kwargs):
        """ Return columns assocated with the table for the job.

        The returned column set includes ephemeral columns associated
        with this job unless ephemeral is set to False.

        """
        if ephemeral is None:
            kwargs['ephemeral'] = self.master or self
        return self.table.get_columns(**kwargs)

    def json(self, data=None):
        """ Return a JSON representation of this Job. """
        return {'id': self.id,
                'handle': self.handle,
                'progress': self.progress,
                'remaining': self.remaining,
                'status': self.status,
                'message': self.message,
                'exception': self.exception,
                'data': data}

    def combine_filterexprs(self, joinstr="and", exprs=None):
        self.refresh()

        if exprs is None:
            exprs = []
        elif type(exprs) is not list:
            exprs = [exprs]

        exprs.append(self.table.filterexpr)

        nonnull_exprs = []
        for e in exprs:
            if e != "" and e is not None:
                nonnull_exprs.append(e)

        if len(nonnull_exprs) > 1:
            return "(" + (") " + joinstr + " (").join(nonnull_exprs) + ")"
        elif len(nonnull_exprs) == 1:
            return nonnull_exprs[0]
        else:
            return ""

    def start(self, method=None, method_args=None):
        """ Start this job. """

        logger.info("%s: Job starting" % self)
        self.refresh()

        if self.is_follower:
            logger.debug("%s: Shadowing master job %s" % (self, self.master))
            return

        # Create an worker to do the work
        worker = Worker(self, method, method_args)
        logger.debug("%s: Created worker %s" % (self, worker))
        worker.start()

    def check_children(self):
        running_children = Job.objects.filter(
            parent=self, status__in=[Job.NEW, Job.RUNNING])

        logger.debug("%s: %d running children" % (self, len(running_children)))

        if len(running_children) > 0:
            # Not done yet, do nothing
            return

        with transaction.atomic():
            # Grab a lock on this job to make sure only one caller
            # gets the callback
            Job.objects.select_for_update().get(id=self.id)

            # Now that we have the lock, make sure we have latest Job
            # details
            self.refresh()

            logger.debug("%s: checking callback %s" % (self, self.callback))
            if self.callback is None:
                # Some other child got to it first
                return

            # Save off the callback, we'll call it outside the transaction
            callback = self.callback

            # Clear the callback while still in lockdown
            self.callback = None
            self.save()

        w = Worker(self, callback=callback)
        logger.debug("%s: Created callback worker %s" % (self, w))
        w.start()

    def schedule(self, jobs, callback):
        jobid_map = {}
        for name, job in jobs.iteritems():
            jobid_map[name] = job.id

        logger.debug("%s: Setting callback %s" % (self, callback))
        self.safe_update(callback=Callable(callback))
        logger.debug("%s: Done setting callback %s" % (self, self.callback))

        for name, job in jobs.iteritems():
            job.start()

    def mark_error(self, message, exception=''):
        logger.warning("%s failed: %s" % (self, message))
        self.safe_update(status=Job.ERROR,
                         progress=100,
                         message=message,
                         exception=exception)
        #
        # Send signal for possible Triggers
        #
        error_signal.send(sender=self,
                          context={'job': self})

    def mark_complete(self, data=None):
        logger.info("%s complete" % self)

        if isinstance(data, list) and len(data) > 0:
            # Convert the result to a dataframe
            columns = [col.name for col in
                       self.get_columns(synthetic=False)]
            df = pandas.DataFrame(data, columns=columns)
        elif ((data is None) or
              (isinstance(data, list) and len(data) == 0)):
            df = None
        elif isinstance(data, pandas.DataFrame):
            df = data
        else:
            raise ValueError("Unrecognized query result type: %s" %
                             type(data))

        if df is not None:
            self.check_columns(df)
            df = self.normalize_types(df)
            df = self.table.compute_synthetic(self, df)

            # Sort according to the defined sort columns
            if self.table.sortcols:
                sorted = df.sort(
                    self.table.sortcols,
                    ascending=[b == Table.SORT_ASC
                               for b in self.table.sortdir]
                )
                # Move NaN rows of the first sortcol to the end
                n = self.table.sortcols[0]
                df = (sorted[sorted[n].notnull()]
                      .append(sorted[sorted[n].isnull()]))

            if self.table.rows > 0:
                df = df[:self.table.rows]

        if df is not None:
            df.to_pickle(self.datafile())

            #
            # Send signal for possible Triggers
            #
            post_data_save.send(sender=self,
                                data=df,
                                context={'job': self})

            logger.debug("%s data saved to file: %s" %
                         (str(self), self.datafile()))
        else:
            logger.debug("%s no data saved, data is empty" %
                         (str(self)))

        logger.info("%s finished as COMPLETE" % self)

        kwargs = dict(status=Job.COMPLETE,
                      progress=100,
                      message='')
        self.refresh()
        if self.actual_criteria is None:
            kwargs['actual_criteria'] = self.criteria

        self.safe_update(**kwargs)
        if self.parent:
            self.parent.check_children()

            followers = Job.objects.filter(master=self)
            for follower in followers:
                if follower.parent:
                    follower.parent.check_children()

    def mark_progress(self, progress, remaining=None):
        # logger.debug("%s progress %s" % (self, progress))
        return
        if self.update_progress:
            self.safe_update(status=Job.RUNNING,
                             progress=progress,
                             remaining=remaining)

    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)

    def data(self):
        """ Returns a pandas.DataFrame of data, or None if not available. """

        with transaction.atomic():
            self.refresh()
            if not self.status == Job.COMPLETE:
                raise DataError("Job not complete, no data available")

            self.reference("data()")

            e = None
            try:
                logger.debug("%s looking for data file: %s" %
                             (str(self), self.datafile()))
                if os.path.exists(self.datafile()):
                    df = pandas.read_pickle(self.datafile())
                    logger.debug("%s data loaded %d rows from file: %s" %
                                 (str(self), len(df), self.datafile()))
                else:
                    logger.debug("%s no data, missing data file: %s" %
                                 (str(self), self.datafile()))
                    df = None
            except Exception as e:
                logger.error("Error loading datafile %s for %s" %
                             (self.datafile(), str(self)))
                logger.error("Traceback:\n%s" % e)
            finally:
                self.dereference("data()")

            if e:
                raise e

            return df

    def values(self):
        """ Return data as a list of lists. """

        df = self.data()
        if df is not None:
            # Replace NaN with None
            df = df.where(pandas.notnull(df), None)

            # Extract tha values in the right order
            all_columns = self.get_columns()
            all_col_names = [c.name for c in all_columns]

            # Straggling numpy data types may cause problems
            # downstream (json encoding, for example), so strip
            # things down to just native ints and floats
            vals = []
            for row in df.ix[:, all_col_names].itertuples():
                vals_row = []
                for v in row[1:]:
                    if (isinstance(v, numpy.number) or
                            isinstance(v, numpy.bool_)):
                        v = numpy.asscalar(v)
                    vals_row.append(v)
                vals.append(vals_row)

        else:
            vals = []
        return vals

    @classmethod
    def age_jobs(cls, old=None, ancient=None, force=False):
        """ Delete old jobs that have no refcount and all ancient jobs. """
        # Throttle - only run this at most once every 15 minutes
        global age_jobs_last_run
        if not force and time.time() - age_jobs_last_run < 60 * 15:
            return

        age_jobs_last_run = time.time()

        if old is None:
            old = datetime.timedelta(
                seconds=settings.APPS_DATASOURCE['job_age_old_seconds']
            )
        elif type(old) in [int, float]:
            old = datetime.timedelta(seconds=old)

        if ancient is None:
            ancient = datetime.timedelta(
                seconds=settings.APPS_DATASOURCE['job_age_ancient_seconds']
            )
        elif type(ancient) in [int, float]:
            ancient = datetime.timedelta(seconds=ancient)

        with transaction.atomic():
            # Ancient jobs are deleted regardless of refcount
            now = datetime.datetime.now(tz=pytz.utc)
            try:
                qs = (Job.objects.select_for_update().
                      filter(touched__lte=now - ancient))
                if len(qs) > 0:
                    logger.info('Deleting %d ancient jobs ...' % len(qs))
                    qs.delete()
            except:
                logger.exception("Failed to delete ancient jobs")

            # Old jobs are deleted only if they have a refcount of 0
            try:
                qs = (Job.objects.select_for_update().
                      filter(touched__lte=now - old, refcount=0))
                if len(qs) > 0:
                    logger.info('Deleting %d old jobs ...' % len(qs))
                    qs.delete()
            except:
                logger.exception("Failed to delete old jobs")

    @classmethod
    def flush_incomplete(cls):
        jobs = Job.objects.filter(progress__lt=100)
        logger.info("Flushing %d incomplete jobs: %s" %
                    (len(jobs), [j.id for j in jobs]))
        jobs.delete()

    def done(self):
        self.refresh()
        # logger.debug("%s status: %s - %s%%" % (str(self),
        #                                       self.status,
        #                                       self.progress))
        return self.status == Job.COMPLETE or self.status == Job.ERROR

    def check_columns(self, df):
        for col in self.get_columns(synthetic=False):
            if col.name not in df:
                raise ValueError(
                    'Returned table missing expected column: %s' % col.name)

    def normalize_types(self, df):
        for col in self.get_columns(synthetic=False):
            s = df[col.name]
            if col.istime():
                # The column is supposed to be time,
                # make sure all values are datetime objects
                if str(s.dtype).startswith(str(pandas.np.dtype('datetime64'))):
                    # Already a datetime
                    pass
                elif str(s.dtype).startswith('int'):
                    # Assume this is a numeric epoch, convert to datetime
                    df[col.name] = s.astype('datetime64[s]')
                elif str(s.dtype).startswith('float'):
                    # This is a numeric epoch as a float, possibly
                    # has subsecond resolution, convert to
                    # datetime but preserve up to millisecond
                    df[col.name] = (1000 * s).astype('datetime64[ms]')
                else:
                    # Possibly datetime object or a datetime string,
                    # hopefully astype() can figure it out
                    df[col.name] = s.astype('datetime64[ms]')

                # Make sure we are UTC, must use internal tzutc because
                # pytz timezones will cause an error when unpickling
                # https://github.com/pydata/pandas/issues/6871
                # -- problem appears solved with latest pandas
                utc = pytz.utc
                try:
                    df[col.name] = df[col.name].apply(lambda x:
                                                      x.tz_localize(utc))
                except BaseException as e:
                    if e.message.startswith('Cannot convert'):
                        df[col.name] = df[col.name].apply(lambda x:
                                                          x.tz_convert(utc))
                    else:
                        raise

            elif (col.isnumeric() and
                  s.dtype == pandas.np.dtype('object')):
                # The column is supposed to be numeric but must have
                # some strings.  Try replacing empty strings with NaN
                # and see if it converts to float64
                try:
                    df[col.name] = (s.replace('', pandas.np.NaN)
                                    .astype(pandas.np.float64))
                except ValueError:
                    # This may incorrectly be tagged as numeric
                    pass

        return df


@receiver(pre_delete, sender=Job)
def _my_job_delete(sender, instance, **kwargs):
    """ Clean up jobs when deleting. """
    # if a job has a master, just deref, don't delete the datafile since
    # that will remove it from the master as well
    if instance.master is not None:
        instance.master.dereference(str(instance))
    elif instance.datafile() and os.path.exists(instance.datafile()):
        try:
            os.unlink(instance.datafile())
        except OSError:
            # permissions issues, perhaps
            logger.error('OSError occurred when attempting to delete '
                         'job datafile: %s' % instance.datafile())


class AsyncWorker(threading.Thread):
    def __init__(self, job, queryclass):
        threading.Thread.__init__(self)
        self.daemon = True
        self.job = job
        self.queryclass = queryclass

        logger.info("%s created" % self)

    def __delete__(self):
        if self.job:
            self.job.dereference("AsyncWorker deleted")

    def __unicode__(self):
        return "<AsyncWorker %s>" % (self.job)

    def __str__(self):
        return "<AsyncWorker %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def run(self):
        self.do_run()
        sys.exit(0)


class SyncWorker(object):
    def __init__(self, job, queryclass):
        self.job = job
        self.queryclass = queryclass

    def __unicode__(self):
        return "<SyncWorker %s>" % (self.job)

    def __str__(self):
        return "<SyncWorker %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def start(self):
        self.do_run()


class CeleryWorker(object):

    def __unicode__(self):
        return "<CeleryWorker %s>" % (self.job)

    def __str__(self):
        return "<CeleryWorker %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def start(self):
        worker_start.delay(self)


@celery.task()
def worker_start(worker):
    worker.call_method()


@celery.task()
def worker_results_callback(results, worker):
    worker.call_method()


if settings.APPS_DATASOURCE['threading'] and not settings.TESTING:
    base_worker_class = AsyncWorker
else:
    base_worker_class = SyncWorker

base_worker_class = CeleryWorker


class Worker(base_worker_class):

    def __init__(self, job, method=None, method_args=None, callback=None):
        job.reference("Worker created")
        # Change to job id?
        self.job = job
        if callback:
            self.callback = callback
        elif method:
            self.callback = Callable(method, method_args)
        else:
            self.callback = Callable(self.queryclass().run)
        self.method_args = method_args
        super(Worker, self).__init__()

    def queryclass(self):
        # Lookup the query class for the table associated with this worker
        i = importlib.import_module(self.job.table.module)
        queryclass = i.__dict__[self.job.table.queryclass]
        return queryclass

    def call_method(self):
        callback = self.callback
        method_args = self.method_args or []
        query = self.queryclass()(self.job)

        try:
            logger.info("%s: running %s(%s)" %
                        (self, callback,
                         ', '.join([str(x) for x in method_args])))
            result = callback(query, *method_args)

            # Backward compatibility mode - run() method returned
            # True or False and set query.data
            if result is True:
                result = QueryComplete(query.data)
            elif result is False:
                result = QueryError(self.job.message or
                                    ("Unknown failure running %s" % callback))

            if result.is_complete():
                # Result is of type QueryComplete
                self.job.mark_complete(result.data)

            elif result.is_error():
                self.job.mark_error(result.message)

            elif result.jobs:
                jobids = {}
                for name, job in result.jobs.iteritems():
                    if job.parent is None:
                        job.safe_update(parent=self.job)
                    jobids[name] = job.id

                callback = Callable(query._post_query_continue,
                                    called_args=(jobids,
                                                 Callable(result.callback)))

                logger.debug("%s: Setting callback %s" % (self.job, callback))
                self.job.safe_update(callback=callback)

                for name, job in result.jobs.iteritems():
                    job.start()

            else:
                # QueryContinue, but no sub-jobs, just reschedule the callback
                self.job.start(result.callback)

        except:
            logger.exception("%s raised an exception" % self)
            self.job.mark_error(
                message="".join(
                    traceback.format_exception_only(*sys.exc_info()[0:2])),
                exception="".join(
                    traceback.format_exception(*sys.exc_info()))
            )

        finally:
            job.dereference("Worker exiting")


class BatchJobRunner(object):

    def __init__(self, basejob, batchsize=4, min_progress=0, max_progress=100):
        self.basejob = basejob
        self.jobs = []
        self.batchsize = batchsize
        self.min_progress = min_progress
        self.max_progress = max_progress

    def __str__(self):
        return "BatchJobRunner (%s)" % self.basejob

    def add_job(self, job):
        self.jobs.append(job)

    def run(self):
        class JobList:
            def __init__(self, jobs):
                self.jobs = jobs
                self.index = 0
                self.count = len(jobs)

            def __nonzero__(self):
                return self.index < self.count

            def next(self):
                if self.index < self.count:
                    job = self.jobs[self.index]
                    self.index += 1
                    return job
                return None

        joblist = JobList(self.jobs)
        done_count = 0
        batch = []

        logger.info("%s: %d total jobs" % (self, joblist.count))

        while joblist and len(batch) < self.batchsize:
            job = joblist.next()
            batch.append(job)
            job.start()
            logger.debug("%s: starting batch job #%d (%s)"
                         % (self, joblist.index, job))

        # iterate until both jobs and batch are empty
        while joblist or batch:
            # check jobs in the batch
            rebuild_batch = False
            batch_progress = 0.0
            something_done = False
            for i, job in enumerate(batch):
                job.refresh()
                if job.done():
                    something_done = True
                    done_count += 1
                    if joblist:
                        batch[i] = joblist.next()
                        batch[i].start()
                        logger.debug("%s: starting batch job #%d (%s)"
                                     % (self, joblist.index, batch[i]))
                    else:
                        batch[i] = None
                        rebuild_batch = True
                else:
                    batch_progress += float(job.progress)

            total_progress = ((float(done_count * 100) + batch_progress)
                              / joblist.count)
            job_progress = (float(self.min_progress) +
                            ((total_progress / 100.0) *
                             (self.max_progress - self.min_progress)))
            # logger.debug(
            #    "%s: progress %d%% (basejob %d%%) (%d/%d done, %d in batch)" %
            #    (self, int(total_progress), int(job_progress),
            #    done_count, joblist.count, len(batch)))
            self.basejob.mark_progress(job_progress)

            if not something_done:
                time.sleep(0.2)

            elif rebuild_batch:
                batch = [j for j in batch if j is not None]

        return
