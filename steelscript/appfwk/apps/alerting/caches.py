# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import threading
from collections import defaultdict

from django.db.models.loading import get_model


logger = logging.getLogger(__name__)
lock = threading.Lock()


class ModelCache(object):
    """Provide quick lookup operation for Model objects by given attribute.

    Since lookup values can be stored as a PickledObjectField, direct filtering
    using query logic won't be reliable, and since the encoding/decoding
    could be expensive across each given model all the time, this class
    pre-caches the values for quicker evaluation.

    This is an in-memory cache and will be re-populated on server
    restarts or cold-calling a run table operation.
    """
    # Override these two values in subclass, set both as strings
    _model = None       # dotted reference to model, e.g. 'appname.Model'
    _key = None         # model attribute to create keys for

    # Leave this value as None
    _lookup = None

    @classmethod
    def debug(cls, msg):
        logger.debug('%s: %s' % (cls.__name__, msg))

    @classmethod
    def _get(cls):
        lock.acquire()
        if cls._lookup is None:
            cls.debug('loading new data')
            cls._lookup = defaultdict(list)

            model = get_model(*cls._model.rsplit('.', 1))
            objects = model.objects.select_related()
            for o in objects:
                key = getattr(o, cls._key)
                cls.debug('adding %s to key %s' % (o, key))
                cls._lookup[key].append(o)
        lock.release()

    @classmethod
    def clear(cls):
        cls.debug('clearing cache')
        cls._lookup = None

    @classmethod
    def filter(cls, value):
        cls.debug('filtering on %s' % value)
        if cls._lookup is None:
            cls._get()
        return cls._lookup[value]
