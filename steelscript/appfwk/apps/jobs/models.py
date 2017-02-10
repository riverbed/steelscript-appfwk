# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import time
import random
import hashlib
import logging
import datetime
import pytz
import pandas
import numpy
import threading

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
from steelscript.common.exceptions import RvbdHTTPException

from steelscript.appfwk.apps.jobs.task import Task
from steelscript.appfwk.apps.jobs.progress import progressd
from steelscript.appfwk.project.locks import TransactionLock

logger = logging.getLogger(__name__)


age_jobs_last_run = 0


class JobManager(models.Manager):

    def get_master(self, handle):
        """Return Job object for master or None if no valid jobs found."""
        master = None

        # Find jobs with the same handle but with no master,
        # these are candidate master jobs.  Lock these rows
        # so we can ensure they don't get deleted until
        # we have a chance to touch it and refcount the selected
        # master below
        candidates = (Job.objects
                      .select_for_update()
                      .filter(status__in=[Job.NEW,
                                          Job.QUEUED,
                                          Job.RUNNING,
                                          Job.COMPLETE],
                              handle=handle,
                              master=None)
                      .order_by('created'))

        if candidates:
            master_jobs = Task.validate_jobs(jobs=candidates, delete=True)
            master = master_jobs[0] if master_jobs else None

        return master

    def age_jobs(self, old=None, ancient=None, force=False):
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
                      filter(touched__lte=now - ancient).
                      order_by('id'))
                if len(qs) > 0:
                    logger.info('Deleting %d ancient jobs ...' % len(qs))
                    qs.delete()
            except:
                logger.exception("Failed to delete ancient jobs")

            # Old jobs are deleted only if they have a refcount of 0
            try:
                qs = (Job.objects.select_for_update().
                      filter(touched__lte=now - old, refcount=0).
                      order_by('id'))
                if len(qs) > 0:
                    logger.info('Deleting %d old jobs ...' % len(qs))
                    qs.delete()
            except:
                logger.exception("Failed to delete old jobs")

    def flush_incomplete(self):
        jobs = Job.objects.exclude(status__in=[Job.COMPLETE, Job.ERROR])
        logger.info("Flushing %d incomplete jobs: %s" %
                    (len(jobs), [j.id for j in jobs]))
        jobs.delete()


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
    QUEUED = 1
    RUNNING = 2
    COMPLETE = 3
    ERROR = 4

    status = models.IntegerField(
        default=NEW,
        choices=((NEW, "New"),
                 (QUEUED, "Queued"),
                 (RUNNING, "Running"),
                 (COMPLETE, "Complete"),
                 (ERROR, "Error")))

    # Process ID for original Task thread
    pid = models.IntegerField(default=None, null=True)

    # Message if job complete or error
    message = models.TextField(default="")

    # If an error comes from a Python exception, this will contain the full
    # exception text with traceback.
    exception = models.TextField(default="")

    # Whether to update detailed progress
    update_progress = models.BooleanField(default=True)

    # Callback function
    callback = CallableField()

    # Manager class for additional .objects methods
    objects = JobManager()

    def __unicode__(self):
        return "<Job %s (%8.8s) - t%s>" % (self.id, self.handle, self.table.id)

    def __repr__(self):
        return unicode(self)

    def json(self, data=None):
        """ Return a JSON representation of this Job. """
        return {'id': self.id,
                'handle': self.handle,
                'progress': self.progress,
                'status': self.status,
                'message': self.message,
                'exception': self.exception,
                'data': data}

    @property
    def progress(self):
        progress = progressd.get(self.id, 'progress')
        logger.debug('***PROGRESS: %s: %s' % (self.id, progress))
        return int(progress)

    @property
    def is_child(self):
        return self.parent is not None

    @property
    def is_follower(self):
        return self.master is not None

    def reference(self, message=""):
        with TransactionLock(self, '%s.reference' % self):
            pk = self.pk
            Job.objects.filter(pk=pk).update(refcount=F('refcount') + 1)
        # logger.debug("%s: reference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def dereference(self, message=""):
        with TransactionLock(self, '%s.dereference' % self):
            pk = self.pk
            Job.objects.filter(pk=pk).update(refcount=F('refcount') - 1)
        # logger.debug("%s: dereference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def refresh(self):
        """ Refresh dynamic job parameters from the database. """
        # fix bug 227119, by avoiding mysql caching problems
        # http://stackoverflow.com/a/7028362
        # should be fixed in Django 1.6
        # XXXCJ -- can we drop this now?
        Job.objects.update()
        job = Job.objects.get(pk=self.pk)
        for k in ['status', 'message', 'exception', 'actual_criteria',
                  'touched', 'refcount', 'callback', 'parent']:
            setattr(self, k, getattr(job, k))

    def safe_update(self, **kwargs):
        """ Update the job with the passed dictionary in a database safe way.

        This method updates only the requested paraemters and refreshes
        the rest from the database.  This should be used for all updates
        to Job's to ensure that unmodified keys are not accidentally
        clobbered by doing a blanket job.save().

        """
        logger.debug("%s safe_update %s" % (self, kwargs))

        with TransactionLock(self, '%s.safe_update' % str(self)):
            Job.objects.filter(pk=self.pk).update(**kwargs)
            self.refresh()

    @classmethod
    def create(cls, table, criteria, update_progress=True, parent=None):

        # Adjust the criteria for this specific table, locking
        # down start/end times as needed
        criteria = criteria.build_for_table(table)
        try:
            criteria.compute_times()
        except ValueError:
            # Ignore errors, this table may not have start/end times
            pass

        # Compute the handle -- this will take into account
        # cacheability
        handle = Job._compute_handle(table, criteria)

        # Grab a lock on the row associated with the table
        with TransactionLock(table, "Job.create"):
            # Look for another job by the same handle in any state except ERROR
            master = Job.objects.get_master(handle)

            job = Job(table=table,
                      criteria=criteria,
                      actual_criteria=None,
                      status=Job.NEW,
                      pid=os.getpid(),
                      handle=handle,
                      parent=parent,
                      master=master,
                      update_progress=update_progress,
                      message='',
                      exception='')
            job.save()

            if master:
                master.reference("Master link from job %s" % job)
                now = datetime.datetime.now(tz=pytz.utc)
                master.safe_update(touched=now)

                logger.info("%s: New job for table %s, linked to master %s"
                            % (job, table.name, master))
            else:
                logger.info("%s: New job for table %s" % (job, table.name))

            # Create new instance in progressd as part of same Transaction
            p = {'job_id': job.id,
                 'status': job.status,
                 'progress': 0,
                 'master_id': job.master.id if job.master else 0,
                 'parent_id': job.parent.id if job.parent else 0
                 }
            logger.debug('***Creating Job to progressd: %s' % p)
            progressd.post(**p)

            # End of TransactionLock

        logger.debug("%s: criteria = %s" % (job, criteria))

        return job

    def start(self, method=None, method_args=None):
        """ Start this job. """

        with TransactionLock(self.table, '%s.start' % self):
            logger.info("%s: Job starting" % self)
            self.refresh()

            if self.is_follower:
                logger.debug("%s: Shadowing master job %s" %
                             (self, self.master))
                if self.master.status == Job.COMPLETE:
                    self.mark_complete()
                elif self.master.status == Job.ERROR:
                    self.mark_error(self.master.message,
                                    self.master.exception)

                return

        if method is None:
            method = self.table.queryclass.run

        # Create an task to do the work
        task = Task(self, Callable(method, method_args))
        logger.debug("%s: Created task %s" % (self, task))
        task.start()

    def schedule(self, jobs, callback):
        jobid_map = {}
        for name, job in jobs.iteritems():
            jobid_map[name] = job.id

        logger.debug("%s: Setting callback %s" % (self, callback))
        self.safe_update(callback=Callable(callback))
        logger.debug("%s: Done setting callback %s" % (self, self.callback))

        for name, job in jobs.iteritems():
            job.start()

    def check_children(self, objlock=None):
        # get a lock on the child that's called us to ensure any status
        # from its transaction will be seen.
        if objlock is None:
            objlock = self

        with TransactionLock(objlock, '%s.checking_children' % self):
            running_children = Job.objects.filter(
                parent=self, status__in=[Job.NEW, Job.RUNNING])

        logger.info("%s: %d running children" % (self, len(running_children)))
        logger.debug("%s: all children: %s" %
                     (self, ';'.join('%s - %s' %
                                     (j.status, j) for j in
                                     Job.objects.filter(parent=self))))

        if len(running_children) > 0:
            # Not done yet, do nothing
            return

        # Grab a lock on this job to make sure only one caller
        # gets the callback
        with TransactionLock(self, '%s.check_children' % self):
            # Now that we have the lock, make sure we have latest Job
            # details
            self.refresh()

            logger.info("%s: checking callback %s" % (self, self.callback))
            if self.callback is None:
                # Some other child got to it first
                return

            # Save off the callback, we'll call it outside the transaction
            callback = self.callback

            # Clear the callback while still in lockdown
            self.callback = None
            self.save()

        t = Task(self, callback=callback)
        logger.info("%s: Created callback task %s" % (self, t))
        t.start()

    def done(self):
        self.status = int(progressd.get(self.id, 'status'))
        if self.status in (Job.COMPLETE, Job.ERROR):
            self.refresh()

        return self.status in (Job.COMPLETE, Job.ERROR)

    def mark_progress(self, progress, status=None):
        if status is None:
            status = Job.RUNNING
        logger.debug('***SAVING PROGRESS for %s: %s/%s' % (self.id, status,
                                                           progress))
        progress = int(float(progress))
        try:
            progressd.put(self.id, status=status, progress=progress)
        except RvbdHTTPException as e:
            logger.debug('***Error saving progress for %s: %s' % (self.id, e))

    def mark_done(self, status, **kwargs):
        with TransactionLock(self, '%s.mark_done' % self):
            self.refresh()
            old_status = self.status
            if old_status in (Job.COMPLETE, Job.ERROR):
                # Status was already set to a done state, avoid
                # double action and return now
                return
            self.status = status
            for k, v in kwargs.iteritems():
                setattr(self, k, v)
            self.save()

        # On status change, do more...
        self.mark_progress(status=status,
                           progress=100)

        if not self.is_follower:
            # Notify followers of this job
            followers = Job.objects.filter(master=self)
            for follower in followers:
                if self.status == Job.COMPLETE:
                    kwargs['actual_criteria'] = self.actual_criteria
                    follower.mark_complete(status=status, **kwargs)

                elif self.status == Job.ERROR:
                    follower.mark_done(status=status, **kwargs)

        if self.parent:
            logger.info("%s: Asking parent %s to check children" %
                        (self, self.parent))
            t = Task(self.parent,
                     callback=Callable(self.parent.check_children,
                                       called_kwargs={'objlock': self}),
                     generic=True)
            logger.info("%s: Created check_children task %s" % (self, t))
            t.start()

        return True

    def mark_complete(self, data=None, **kwargs):
        logger.info("%s: complete" % self)
        if data is not None:
            self._save_data(data)

        kwargs['status'] = Job.COMPLETE
        kwargs['message'] = ''

        if (self.actual_criteria is None and 'actual_criteria' not in kwargs):
            kwargs['actual_criteria'] = self.criteria

        self.mark_done(**kwargs)
        logger.info("%s: saved as COMPLETE" % self)

        # Send signal for possible Triggers
        post_data_save.send(sender=self,
                            data=self.data,
                            context={'job': self})

    def mark_error(self, message, exception=None):
        if exception is None:
            exception = ''

        logger.warning("%s failed: %s" % (self, message))

        self.mark_done(status=Job.ERROR,
                       message=message,
                       exception=exception)
        logger.info("%s: saved as ERROR" % self)

        # Send signal for possible Triggers
        error_signal.send(sender=self,
                          context={'job': self})

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

    def get_columns(self, ephemeral=None, **kwargs):
        """ Return columns assocated with the table for the job.

        The returned column set includes ephemeral columns associated
        with this job unless ephemeral is set to False.

        """
        if ephemeral is None:
            kwargs['ephemeral'] = self.master or self
        return self.table.get_columns(**kwargs)

    def _save_data(self, data):
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
                sorted = df.sort_values(
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

            logger.debug("%s data saved to file: %s" %
                         (str(self), self.datafile()))
        else:
            logger.debug("%s no data saved, data is empty" %
                         (str(self)))

        return df

    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)

    def data(self):
        """ Returns a pandas.DataFrame of data, or None if not available. """

        if not self.done():
            logger.warning(
                "%s: job not complete, no data available" % self)
            raise DataError(
                "Job not complete, no data available")

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
                except TypeError as e:
                    if e.message.startswith('Cannot localize'):
                        df[col.name] = df[col.name].apply(lambda x:
                                                          x.tz_convert(utc))
                    else:
                        raise
            elif col.isdate():
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
                elif str(s.dtype).startswith('object'):
                    # This is a datetime.date object, convert it to
                    # datetime64[ns], tried to obtain datetime64[s]
                    # by setting unit='s' but failed
                    # It seems datetime64[ns] is accepted.
                    df[col.name] = pandas.to_datetime(s)
                else:
                    # Possibly datetime object or a datetime string,
                    # hopefully astype() can figure it out
                    df[col.name] = s.astype('datetime64[ms]')
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

    try:
        progressd.delete(instance.pk)
    except BaseException as e:
        logger.error('Error deleting %s from progressd: %s' % (instance, e))


class BatchJobRunner(object):

    def __init__(self, basejob, batchsize=4, min_progress=0, max_progress=100):
        raise Exception("BatchJobRunner is obsolete, please update your code")

    def __str__(self):
        return "BatchJobRunner (%s)" % self.basejob

    def add_job(self, job):
        pass

    def run(self):
        pass
