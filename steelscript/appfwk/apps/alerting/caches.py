# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import threading
from collections import defaultdict

from django.apps import apps
from steelscript.appfwk.apps.alerting.source import Source

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

            model = apps.get_model(*cls._model.rsplit('.', 1))
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
        if not isinstance(value, frozenset):
            value = Source.encode(value)
        return cls._lookup[value]


class GlobalCache(Cache):
    """This class provides functionality to load a list of dicts and
    populate  in-memory cache with a list of django model objects. It also
    provides an interface to iterate through the cache data.

    This class will not be used directly. It will be only used by its
    subclasses, with defined _source, _default_func and _model.

    _source: a list of python dicts;
    _model: the dotted reference to the django model, e.g. 'app_name.Model'
    _default_func: a function which returns a default value if some
        _model's field is not found in one dict in _source.

    Below shows how this class should be used.
        class OneClass(models.Model):
            x = models.IntegerField()
            y = models.IntegerField()
            z = models.IntegerField()

            @classmethod
            def create(cls, x, y=None, z=None):
                return OneClass(x=x,y=y,z=z)

        class OneClassCache(GlobalCache):
            _source = ({'x': 1,
                        'y': 2},)
            _model = 'app_name.OneClass' #app_name is the application name
            _default_func = lambda: 3

        for one_object in OneClassCache.data():
            'the value of one_object.z is 3'
    """
    # Override these three values in subclass
    _source = None        # list/tuple of dicts to populate _model object
    _default_func = None  # Default func of each key in the dict
    _model = None          # dotted reference to model, e.g. 'appname.Model'

    # Leave this value as None
    _lookup = None

    @classmethod
    def _get(cls):
        lock.acquire()
        if cls._lookup is None:
            cls.debug('loading new data')
            cls._lookup = []
            cls._model = apps.get_model(*cls._model.rsplit('.', 1))
            for one in cls._source:
                # create defaultdict 'one_dict' using dict 'one' and
                # _default_func, where one_dict is used as a list of keyword
                # arguments, and if some keyword are missing from dict 'one'
                # according to function cls._model.create, then the missing
                # keyword arguments will be automatically added in 'one_dict'
                # using the value returned from cls._default_func
                one_dict = defaultdict(cls._default_func, one)
                cls._lookup.append(cls._model.create(**one_dict))
        lock.release()

    @classmethod
    def data(cls):
        if cls._lookup is None:
            cls._get()
        return iter(cls._lookup)
