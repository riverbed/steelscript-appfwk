# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import sys
import logging
import traceback

from steelscript.appfwk.libs.fields import Callable

logger = logging.getLogger(__name__)


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

    def __init__(self, message=None, exception=None):
        super(QueryError, self).__init__(QueryResponse.QUERY_ERROR)
        self.message = message
        self.exception = exception


class BaseTask(object):

    def __init__(self, job, callback, generic=False):
        job.reference("Task created")
        # Change to job id?
        self.job = job
        self.callback = callback
        self.generic = generic

    def __unicode__(self):
        return "<%s %s %s>" % (self.__class__, self.job, self.callback)

    def __str__(self):
        return "<%s %s %s>" % (self.__class__, self.job, self.callback)

    def __repr__(self):
        return unicode(self)

    def call_method(self):
        if self.generic:
            return self._call_generic_method()
        else:
            return self._call_query_method()

    def _call_query_method(self):
        """ Run query-based Job. """
        callback = self.callback

        # Instantiate the query class - this gets used as 'self' object
        # for 'callback', which is a reference to an unbound instance method
        query = self.job.table.queryclass(self.job)

        try:
            logger.info("%s: running %s()" % (self, callback))
            result = callback(query)

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
                self.job.mark_error(result.message, result.exception)

            elif result.jobs:
                # QueryContinue with dependent jobs
                jobids = {}
                for name, job in result.jobs.iteritems():
                    if job.parent is None:
                        # Just in case caller forgot to set the
                        # parent...
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
                # QueryContinue, but no dependent jobs, just
                # reschedule the callback
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
            self.job.dereference("Task exiting")

    def _call_generic_method(self):
        """ Run generic Job operations. """
        callback = self.callback

        try:
            logger.info("%s: running %s()" % (self, callback))
            callback(self.job)

        except:
            logger.exception("%s raised an exception" % self)
            self.job.mark_error(
                    message="".join(
                            traceback.format_exception_only(*sys.exc_info()[0:2])),
                    exception="".join(
                            traceback.format_exception(*sys.exc_info()))
            )

        finally:
            self.job.dereference("Task exiting")

    @classmethod
    def validate_jobs(cls, jobs, delete=False):
        """Validate the given list of jobs and optionally delete invalid ones.

        :param jobs list: List of Job objects to validate
        :param delete bool: If true, all invalid Jobs will be deleted

        :returns: list of valid Job objects
        """
        # default will ignore any validation
        return jobs
