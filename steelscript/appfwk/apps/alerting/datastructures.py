# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import itertools

import pandas

logger = logging.getLogger(__name__)

DEFAULT_SEVERITY = 0    # Default severity when none assigned from trigger
ERROR_SEVERITY = 99     # Severity assigned to all errors


class AlertLevels(object):
    # enumerated list matching logging levels
    FATAL = 'FATAL'
    CRITICAL = 'CRITICAL'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'

    @classmethod
    def find(cls, value):
        """Get level based on given value, returns None if level not found."""
        return getattr(cls, (value or '').upper(), None)

    @classmethod
    def get_levels(cls):
        """Return class-defined levels."""
        return [k for k, v in cls.__dict__.iteritems()
                if (not k.startswith('__') and not hasattr(v, '__func__'))]

    @classmethod
    def get_integer(cls, level):
        """Return integer-value for given level."""
        return getattr(logging, getattr(cls, level))

    @classmethod
    def get_choices(cls):
        lvls = cls.get_levels()
        return zip(lvls, lvls)


class Results(object):
    """Container data structure for annotated trigger method results.

    Stores data in an internal list of dicts.  The keys for each
    dict must be consistent - once the initial data gets stored all
    further data additions must use the same set of keys.

    The 'severity' key is optional, and leaving it blank will default it
    to the integer 0.

    Add data using either .add_result or .add_results methods, the former
    syntax for singleton data elements and the latter for sequences of data.

    In the .add_results case, the supporting keys may also be lists, but they
    must be of the same length as the data.  Alternately, the keys may be
    single-values, in which case that value will be applied to all elements of
    the data list.

    The .add_results method also supports pandas DataFrames as data objects,
    which will be converted internally to a list of dicts.  If a DataFrame
    is passed to the singleton method, it will just be stored as an object
    without conversion.

    # >>> r = Results()
    # >>> r.add_result(88, threshold=80)
    # >>> r.get_data()
    # [{'data': 88, 'threshold': 80, 'severity': 0}]
    # >>> r.add_results([42, 64], threshold=40, severity=[20, 30])
    # >>> r.get_data()
    # [{'data': 88, 'threshold': 80, 'severity': 0},
    #  {'data': 42, 'threshold': 40, 'severity': 20},
    #  {'data': 64, 'threshold': 40, 'severity': 30}]
    """
    def __init__(self):
        self._keys = None
        self._data = []

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return "<Results items: %d keys: %s>" % (len(self._data), self._keys)

    def __unicode__(self):
        return str(self)

    def __repr__(self):
        return unicode(self)

    def _validate_keys(self, severity, **kwargs):
        if severity is None:
            severity = DEFAULT_SEVERITY
        kwargs['severity'] = severity

        keys = set(kwargs.keys())
        if self._keys is None:
            self._keys = keys

        if keys - self._keys:
            msg = 'Invalid keys passed to add_data: %s' % (keys - self._keys)
            raise ValueError(msg)
        elif self._keys - keys:
            msg = 'Missing data keys in add_data: %s' % (self._keys - keys)
            raise ValueError(msg)

        return kwargs

    def _add_items(self, **kwargs):
        try:
            kvs = zip(*[[(k, v) for v in val] for k, val in kwargs.items()])
            items = map(dict, kvs)
        except TypeError:
            # single values rather than lists
            items = [dict([(k, v) for k, v in kwargs.items()])]
        self._data.extend(items)

    def add_result(self, data, severity=None, **kwargs):
        """Add single set of results.

        :param data: single object
        :param severity: integer
        :param kwargs: keyword singletons
        """

        kws = self._validate_keys(severity, **kwargs)
        self._add_items(data=data, **kws)
        return self

    def add_results(self, data, severity=None, **kwargs):
        """Add list of results.

        :param data: list, tuple, or pandas DataFrame
        :param severity: int or list of ints same length as data
        :param kwargs: keyword singletons or list same length as data
        """

        kws = self._validate_keys(severity, **kwargs)
        if isinstance(data, pandas.DataFrame):
            data = data.to_dict('records')

        attrs = {}
        for k in self._keys:
            if isinstance(kws[k], (list, tuple)):
                if len(data) != len(kws[k]):
                    msg = 'Length of %s does not match length of data' % k
                    raise ValueError(msg)
                attrs[k] = kws[k]
            else:
                attrs[k] = itertools.repeat(kws[k], len(data))

        self._add_items(data=data, **attrs)
        return self

    def get_data(self):
        return self._data
