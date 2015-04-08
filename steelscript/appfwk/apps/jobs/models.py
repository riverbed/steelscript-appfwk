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

import pytz
import pandas
import numpy
from django.db import models
from django.db import transaction
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings
from steelscript.appfwk.apps.datasource.models import Table

from steelscript.appfwk.apps.datasource.exceptions import DataError
from steelscript.appfwk.apps.alerting.models import (post_data_save,
                                                     error_signal)
from steelscript.appfwk.libs.fields import PickledObjectField
from steelscript.common.connection import Connection
from steelscript.common.exceptions import RvbdHTTPException


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


# progressd connection
progressd = Connection(settings.PROGRESSD_HOST,
                       port=settings.PROGRESSD_PORT)


class Job(models.Model):

    # Timestamp when the job was created
    created = models.DateTimeField(auto_now_add=True)

    # Timestamp the last time the job was accessed
    touched = models.DateTimeField(auto_now_add=True)

    # Number of references to this job
    refcount = models.IntegerField(default=0)

    # Whether this job is a child of another job
    ischild = models.BooleanField(default=False)

    # If ischild, this points to the parent job
    parent = models.ForeignKey('self', null=True)

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

    _status = models.IntegerField(
        default=NEW,
        choices=((NEW, "New"),
                 (RUNNING, "Running"),
                 (COMPLETE, "Complete"),
                 (ERROR, "Error")))

    # Process ID for original Worker thread
    pid = models.IntegerField(default=None, null=True)

    # Message if job complete or error
    message = models.TextField(default="")

    # If an error comes from a Python exception, this will contain the full
    # exception text with traceback.
    exception = models.TextField(default="")

    # Whether to update detailed progress
    update_progress = models.BooleanField(default=True)

    # While RUNNING, this provides an indicator of progress 0-100
    _progress = models.IntegerField(default=-1)

    # While RUNNING, time remaining
    remaining = models.IntegerField(default=None, null=True)

    def __unicode__(self):
        return "<Job %s (%8.8s) - t%s>" % (self.id, self.handle, self.table.id)

    def __repr__(self):
        return unicode(self)

    def _get_progress(self, attr):
        # Query progressd, but fall back on db value if failed
        try:
            r = progressd.json_request('GET', '/jobs/%d/' % self.id)
            return r[attr]
        except RvbdHTTPException:
            logger.error('progressd lookup failed, using db status values.')
            return getattr(self, '_' + attr)

    @property
    def status(self):
        status = self._get_progress('status')
        logger.debug('***STATUS: %s: %s' % (self.id, status))
        return int(status)

    @property
    def progress(self):
        progress = self._get_progress('progress')
        logger.debug('***PROGRESS: %s: %s' % (self.id, progress))
        return int(progress)

    def refresh(self):
        """ Refresh dynamic job parameters from the database. """
        # fix bug 227119, by avoiding mysql caching problems
        # http://stackoverflow.com/a/7028362
        # should be fixed in Django 1.6
        Job.objects.update()
        job = Job.objects.get(pk=self.pk)
        for k in ['_status', 'message', 'exception', '_progress', 'remaining',
                  'actual_criteria', 'touched', 'refcount']:
            setattr(self, k, getattr(job, k))

    @transaction.commit_on_success
    def safe_update(self, **kwargs):
        """ Update the job with the passed dictionary in a database safe way.

        This method updates only the requested paraemters and refreshes
        the rest from the database.  This should be used for all updates
        to Job's to ensure that unmodified keys are not accidentally
        clobbered by doing a blanket job.save().

        """

        if kwargs is None:
            return

        with LocalLock():
            # logger.debug("%s safe_update %s" % (self, kwargs))
            Job.objects.filter(pk=self.pk).update(**kwargs)

            # Force a reload of the job to get latest data
            self.refresh()

            if not self.ischild:
                # Push changes to children of this job
                child_kwargs = {}
                for k, v in kwargs.iteritems():
                    if k in ['_status', 'message', 'exception', '_progress',
                             'remaining', 'actual_criteria']:
                        child_kwargs[k] = v
                # There should be no recursion, so a direct update to the
                # database is possible.  (If recursion, would need to call
                # self_update() on each child.)
                Job.objects.filter(parent=self).update(**child_kwargs)

    @classmethod
    def create(cls, table, criteria, update_progress=True):

        with LocalLock():
            with transaction.commit_on_success():
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
                parents = []

                if not criteria.ignore_cache:
                    parent_jobs = (Job.objects
                                   .select_for_update()
                                   .filter(_status__in=[Job.NEW,
                                                        Job.COMPLETE,
                                                        Job.RUNNING],
                                           handle=handle,
                                           ischild=False)
                                   .order_by('created'))

                    # check if incomplete jobs are still running by sending
                    # a harmless signal 0 to that PID
                    # or if jobs were never started and even given a PID
                    def pid_active(pid):
                        try:
                            os.kill(pid, 0)
                            return True
                        except OSError:
                            return False

                    for p in parent_jobs:
                        if p.status in (Job.NEW, Job.RUNNING):
                            if p.pid is None or not pid_active(p.pid):
                                logging.debug('*** Deleting stale job %s, '
                                              'with PID %s' % (p, p.pid))
                                p.delete()
                                continue

                        parents.append(p)

                if len(parents) > 0:
                    # since all parents are valid, pick the first one
                    parent = parents[0]

                    job = Job(table=table,
                              criteria=criteria,
                              actual_criteria=parent.actual_criteria,
                              _status=parent._status,
                              pid=os.getpid(),
                              handle=handle,
                              parent=parent,
                              ischild=True,
                              update_progress=parent.update_progress,
                              _progress=parent._progress,
                              remaining=parent.remaining,
                              message='',
                              exception='')
                    job.save()

                    parent.reference("Link from job %s" % job)
                    now = datetime.datetime.now(tz=pytz.utc)
                    parent.safe_update(touched=now)

                    logger.info("%s: New job for table %s, linked to parent %s"
                                % (job, table.name, parent))
                else:
                    job = Job(table=table,
                              criteria=criteria,
                              _status=Job.NEW,
                              pid=os.getpid(),
                              handle=handle,
                              parent=None,
                              ischild=False,
                              update_progress=update_progress,
                              _progress=0,
                              remaining=-1,
                              message='',
                              exception='')
                    job.save()
                    logger.info("%s: New job for table %s" % (job, table.name))

                # Create new instance in progressd
                p = {'job_id': job.id,
                     'status': job._status,
                     'progress': job._progress,
                     'parent_id': job.parent.id if job.parent else 0}
                logger.debug('***Saving Job progress to progressd: %s' % p)
                r = progressd.json_request('POST', '/jobs/', body=p)
                logger.debug('***Result of save: %s' % r)

                logger.debug("%s: criteria = %s" % (job, criteria))

            # Flush old jobs
            Job.age_jobs()

        return job

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
            kwargs['ephemeral'] = self.parent or self
        return self.table.get_columns(**kwargs)

    def json(self, data=None):
        """ Return a JSON representation of this Job. """
        return {'id': self.id,
                'handle': self.handle,
                'progress': self.progress,
                'remaining': self.remaining,
                'status': self._status,
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

    def start(self):
        """ Start this job. """

        self.refresh()

        if self.ischild:
            logger.debug("%s: Shadowing parent job %s" % (self, self.parent))
            return

        with transaction.commit_on_success():
            logger.debug("%s: Starting job" % str(self))
            self.mark_progress(0)

            logger.debug("%s: Worker to run report" % str(self))
            # Lookup the query class for this table
            i = importlib.import_module(self.table.module)
            queryclass = i.__dict__[self.table.queryclass]

            # Create an worker to do the work
            worker = Worker(self, queryclass)
            worker.start()

    def mark_progressd(self, **kwargs):
        logger.debug('***SAVING STATUS: %s: %s' % (self.id, kwargs))
        r = progressd.json_request('PUT', '/jobs/%d/' % self.id, body=kwargs)
        if not r.ok:
            logger.debug('***ERROR SAVING STATUS for %s: %s' % (self.id,
                                                                r.text))

    def mark_error(self, message, exception=''):
        logger.warning("%s failed: %s" % (self, message))
        self.mark_progressd(status=Job.ERROR,
                            progress=100)
        self.safe_update(_status=Job.ERROR,
                         _progress=100,
                         message=message,
                         exception=exception)

    def mark_complete(self):
        logger.info("%s complete" % self)
        self.mark_progressd(status=Job.COMPLETE,
                            progress=100)

        self.safe_update(_status=Job.COMPLETE,
                         _progress=100,
                         message='')

    def mark_progress(self, progress, remaining=None):
        progress = int(float(progress))

        self.mark_progressd(status=Job.RUNNING,
                            progress=progress)

        # still needed?
        if self.update_progress:
            self.safe_update(_status=Job.RUNNING,
                             _progress=progress,
                             remaining=remaining)

    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)

    def data(self):
        """ Returns a pandas.DataFrame of data, or None if not available. """

        with transaction.commit_on_success():
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

        with transaction.commit_on_success():
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
        jobs = Job.objects.filter(_progress__lt=100)
        logger.info("Flushing %d incomplete jobs: %s" %
                    (len(jobs), [j.id for j in jobs]))
        jobs.delete()

    def done(self):
        self.refresh()
        # logger.debug("%s status: %s - %s%%" % (str(self),
        #                                       self.status,
        #                                       self.progress))
        return self.status == Job.COMPLETE or self.status == Job.ERROR


@receiver(pre_delete, sender=Job)
def _my_job_delete(sender, instance, **kwargs):
    """ Clean up jobs when deleting. """
    # if a job has a parent, just deref, don't delete the datafile since
    # that will remove it from the parent as well
    if instance.parent is not None:
        instance.parent.dereference(str(instance))
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
        job.reference("AsyncWorker created")

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


if settings.APPS_DATASOURCE['threading'] and not settings.TESTING:
    base_worker_class = AsyncWorker
else:
    base_worker_class = SyncWorker


class Worker(base_worker_class):

    def __init__(self, job, queryclass):
        super(Worker, self).__init__(job, queryclass)

    def do_run(self):
        job = self.job
        try:
            logger.info("%s running queryclass %s" % (self, self.queryclass))
            query = self.queryclass(job.table, job)

            if (query.pre_run() and
                    query.run() and
                    query.post_run()):

                logger.info("%s query finished" % self)
                if isinstance(query.data, list) and len(query.data) > 0:
                    # Convert the result to a dataframe
                    columns = [col.name for col in
                               job.get_columns(synthetic=False)]
                    df = pandas.DataFrame(query.data, columns=columns)
                elif ((query.data is None) or
                      (isinstance(query.data, list) and len(query.data) == 0)):
                    df = None
                elif isinstance(query.data, pandas.DataFrame):
                    df = query.data
                else:
                    raise ValueError("Unrecognized query result type: %s" %
                                     type(query.data))

                if df is not None:
                    self.check_columns(df)
                    df = self.normalize_types(df)
                    df = job.table.compute_synthetic(job, df)

                    # Sort according to the defined sort columns
                    if job.table.sortcols:
                        sorted = df.sort(
                            job.table.sortcols,
                            ascending=[b == Table.SORT_ASC
                                       for b in job.table.sortdir]
                        )
                        # Move NaN rows of the first sortcol to the end
                        n = job.table.sortcols[0]
                        df = (sorted[sorted[n].notnull()]
                              .append(sorted[sorted[n].isnull()]))

                    if job.table.rows > 0:
                        df = df[:job.table.rows]

                if df is not None:
                    df.to_pickle(job.datafile())

                    #
                    # Send signal for possible Triggers
                    #
                    post_data_save.send(sender=self,
                                        data=df,
                                        context={'job': job})

                    logger.debug("%s data saved to file: %s" %
                                 (str(self), job.datafile()))
                else:
                    logger.debug("%s no data saved, data is empty" %
                                 (str(self)))

                logger.info("%s finished as COMPLETE" % self)
                job.refresh()
                if job.actual_criteria is None:
                    job.safe_update(actual_criteria=job.criteria)

                job.mark_complete()
            else:
                # If the query.run() function returns false, the run() may
                # have set the job.status, check and update if not
                vals = {}
                job.refresh()
                if not job.done():
                    vals['status'] = job.ERROR
                if job.message == "":
                    vals['message'] = "Query returned an unknown error"
                vals['progress'] = 100
                job.safe_update(**vals)
                logger.error("%s finished with an error: %s" % (self,
                                                                job.message))

        except:
            logger.exception("%s raised an exception" % self)
            job.safe_update(
                _status=job.ERROR,
                _progress=100,
                message="".join(
                    traceback.format_exception_only(*sys.exc_info()[0:2])),
                exception="".join(
                    traceback.format_exception(*sys.exc_info()))
            )
            #
            # Send signal for possible Triggers
            #
            error_signal.send(sender=self,
                              context={'job': job})

        finally:
            job.dereference("Worker exiting")

    def check_columns(self, df):
        job = self.job
        for col in job.get_columns(synthetic=False):
            if col.name not in df:
                raise ValueError(
                    'Returned table missing expected column: %s' % col.name)

    def normalize_types(self, df):
        job = self.job
        for col in job.get_columns(synthetic=False):
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
