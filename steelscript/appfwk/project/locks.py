# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
import threading

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

"""
This module defines two classes, ClassLock and TransactionLock.  ClassLock
works at a model level for performing transaction locks, and TransactionLock
works at a model *instance* level.

Since SQLite doesn't support row locking (select_for_update()), we need
to use a threading lock.  This provides support when running
the dev server.  It will not work across multiple processes, only
between threads of a single process
"""


if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):
    lock = threading.RLock()

    class _SQLLock(object):

        def __init__(self, obj, context=""):
            self.obj = obj
            self.context = context

        def __enter__(self):
            logger.debug("%s.enter: %s - %s" % (self.__class__.__name__,
                                                self.context, self.obj))
            lock.acquire()

        def __exit__(self, type_, value, traceback_):
            lock.release()
            logger.debug("%s.exit: %s - %s" % (self.__class__.__name__,
                                               self.context, self.obj))

    class ClassLock(_SQLLock):
        pass

    class TransactionLock(_SQLLock):
        pass

else:
    class _DBLock(transaction.Atomic):
        def __init__(self, obj, context=""):
            super(_DBLock, self).__init__(using=None, savepoint=True)
            self.obj = obj
            self.context = context

        def __enter__(self):
            logger.debug("%s.enter: %s - %s" % (self.__class__.__name__,
                                                self.context, self.obj))
            super(_DBLock, self).__enter__()

        def __exit__(self, type_, value, traceback_):
            r = super(_DBLock, self).__exit__(type_, value, traceback_)
            logger.debug("%s.exit: %s - %s" % (self.__class__.__name__,
                                               self.context, self.obj))
            return r

    class ClassLock(_DBLock):
        pass

    class TransactionLock(_DBLock):
        def __enter__(self):
            super(TransactionLock, self).__enter__()
            self.obj.__class__.objects.select_for_update().get(id=self.obj.id)
