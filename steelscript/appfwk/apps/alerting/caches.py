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


class Cache(object):
    """Base class for ModelCache and GlobalCache"""
    # Leave this value as None
    _lookup = None

    @classmethod
    def debug(cls, msg):
        logger.debug('%s: %s' % (cls.__name__, msg))

    @classmethod
    def clear(cls):
        cls.debug('clearing cache')
        cls._lookup = None


class ModelCache(Cache):
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
    def filter(cls, value):
        cls.debug('filtering on %s' % value)
        if cls._lookup is None:
            cls._get()
        return cls._lookup[value]


class GlobalCache(Cache):
    """Provide loading and iterating ability against data configured
    in local_settings.py

    This is in-memory cache and will be re-populated depending on the
    scenario where the specific cache data will be used.
    """

    _source = None        # Macro for the Global Config Data
    _default_func = None  # Default func of each key in the dict
    _class = None         # the name of class to create object
    _lookup = None

    @classmethod
    def _get(cls):
        lock.acquire()
        if cls._lookup is None:
            cls.debug('loading new data')
            cls._lookup = []
            for one in cls._source:
                one_dict = defaultdict(cls._default_func, one)
                cls._lookup.append(cls._class.create(**one_dict))
        lock.release()

    @classmethod
    def data(cls):
        if cls._lookup is None:
            cls._get()
        return iter(cls._lookup)
