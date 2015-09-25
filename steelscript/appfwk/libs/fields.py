# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
import importlib

from copy import deepcopy
from base64 import b64encode, b64decode
from zlib import compress, decompress
try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps

from django.db import models
from django.utils.encoding import force_unicode

logger = logging.getLogger(__name__)


# see http://djangosnippets.org/snippets/1694/
# and http://djangosnippets.org/snippets/2346/

class FunctionError(Exception):
    pass


class ClassError(Exception):
    pass


class PickledObject(str):
    """
    A subclass of string so it can be told whether a string is a pickled
    object or not (if the object is an instance of this class then it must
    [well, should] be a pickled one).

    Only really useful for passing pre-encoded values to ``default``
    with ``dbsafe_encode``, not that doing so is necessary. If you
    remove PickledObject and its references, you won't be able to pass
    in pre-encoded values anymore, but you can always just pass in the
    python objects themselves.

    """
    pass


def dbsafe_encode(value, compress_object=False):
    """
    We use deepcopy() here to avoid a problem with cPickle, where dumps
    can generate different character streams for same lookup value if
    they are referenced differently.

    The reason this is important is because we do all of our lookups as
    simple string matches, thus the character streams must be the same
    for the lookups to work properly. See tests.py for more information.
    """
    if not compress_object:
        value = b64encode(dumps(deepcopy(value)))
    else:
        value = b64encode(compress(dumps(deepcopy(value))))
    return PickledObject(value)


def dbsafe_decode(value, compress_object=False):
    if not compress_object:
        value = loads(b64decode(value))
    else:
        value = loads(decompress(b64decode(value)))
    return value


class PickledObjectField(models.Field):
    """
    A field that will accept *any* python object and store it in the
    database. PickledObjectField will optionally compress it's values if
    declared with the keyword argument ``compress=True``.

    Does not actually encode and compress ``None`` objects (although you
    can still do lookups using None). This way, it is still possible to
    use the ``isnull`` lookup type correctly. Because of this, the field
    defaults to ``null=True``, as otherwise it wouldn't be able to store
    None values since they aren't pickled and encoded.

    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.compress = kwargs.pop('compress', False)
        self.protocol = kwargs.pop('protocol', 2)
        kwargs.setdefault('null', True)
        kwargs.setdefault('editable', False)
        super(PickledObjectField, self).__init__(*args, **kwargs)

    def get_default(self):
        """
        Returns the default value for this field.

        The default implementation on models.Field calls force_unicode
        on the default, which means you can't set arbitrary Python
        objects as the default. To fix this, we just return the value
        without calling force_unicode on it. Note that if you set a
        callable as a default, the field will still call it. It will
        *not* try to pickle and encode it.

        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        # If the field doesn't have a default, then we punt to models.Field.
        return super(PickledObjectField, self).get_default()

    def to_python(self, value):
        """
        B64decode and unpickle the object, optionally decompressing it.

        If an error is raised in de-pickling and we're sure the value is
        a definite pickle, the error is allowed to propogate. If we
        aren't sure if the value is a pickle or not, then we catch the
        error and return the original value instead.

        """
        if value is not None:
            try:
                value = dbsafe_decode(value, self.compress)

            except (AttributeError, SyntaxError, ImportError):
                raise

            except Exception as e:
                # If the value is a definite pickle; and an error is raised in
                # de-pickling it should be allowed to propogate.
                if isinstance(value, PickledObject):
                    raise

        return value

    def get_prep_value(self, value):
        """
        Pickle and b64encode the object, optionally compressing it.

        The pickling protocol is specified explicitly (by default 2),
        rather than as -1 or HIGHEST_PROTOCOL, because we don't want the
        protocol to change over time. If it did, ``exact`` and ``in``
        lookups would likely fail, since pickle would now be generating
        a different string.

        """
        if value is not None and not isinstance(value, PickledObject):
            # We call force_unicode here explicitly, so that the encoded string
            # isn't rejected by the postgresql_psycopg2 backend. Alternatively,
            # we could have just registered PickledObject with the psycopg
            # marshaller (telling it to store it like it would a string), but
            # since both of these methods result in the same value being
            # stored, doing things this way is much easier.
            value = force_unicode(dbsafe_encode(value, self.compress))
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

    def get_internal_type(self):
        return 'TextField'

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type not in ['exact', 'isnull']:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        return self.get_prep_value(value)


class Function(object):
    """Serializable object for callable objects with their parameters."""
    def __init__(self, function=None, params=None):
        if function:
            self.module = function.__module__
            self.function = function.func_name
        else:
            self.module = None
            self.function = None

        self.params = params

    def __repr__(self):
        return "<Function %s:%s>" % (self.module, self.function)

    def __str__(self):
        return "Function %s:%s" % (self.module, self.function)

    @classmethod
    def from_dict(cls, d):
        self = Function()

        self.module = d['module']
        self.function = d['function']
        self.params = d['params']

        return self

    def to_dict(self):
        return {'module': self.module,
                'function': self.function,
                'params': self.params}

    def __call__(self, *args, **kwargs):
        try:
            mod = importlib.import_module(self.module)
            func = mod.__dict__[self.function]
        except ImportError:
            raise FunctionError(
                "Function reference is invalid, could not import module <%s>"
                % self.module)
        except KeyError:
            raise FunctionError(
                "Function reference is invalid, could not find function "
                "<%s> in module <%s>"
                % (self.function, self.module))

        if 'params' in func.func_code.co_varnames:
            kwargs['params'] = self.params

        return func(*args, **kwargs)


class FunctionField(PickledObjectField):
    """Model field which stores a Function object."""

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if isinstance(value, Function):
            return value

        value = super(FunctionField, self).to_python(value)
        if value is not None:
            return Function.from_dict(value)
        else:
            return None

    def get_prep_value(self, value):
        if value is not None:
            value = super(FunctionField, self).get_prep_value(value.to_dict())
        return value


class CallableError(Exception):
    pass


class Callable(object):
    """Serializable object for callable objects with their parameters.

    This class is similar to Function, except that it supports class
    methods in addition to functions.  In the event that a class method
    is used, it is the responsibility of the caller after serialization
    to provide an object of the same class as the first argument.

    """
    def __init__(self, callable=None, called_args=None, called_kwargs=None):
        if callable:
            if hasattr(callable, 'im_func'):
                # This is a class method
                self.classname = callable.im_class.__name__
                self.module = callable.im_class.__module__
                self.function = callable.im_func.func_name
            else:
                self.module = callable.__module__
                self.function = callable.func_name
                self.classname = None
        else:
            self.module = None
            self.function = None
            self.classname = None

        self.called_args = called_args
        self.called_kwargs = called_kwargs

    def __repr__(self):
        return "<Function %s:%s>" % (self.module, self.function)

    def __str__(self):
        return "Function %s:%s" % (self.module, self.function)

    @classmethod
    def from_dict(cls, d):
        self = Callable()

        self.module = d['module']
        self.function = d['function']
        self.classname = d['classname']
        self.called_args = d['called_args']
        self.called_kwargs = d['called_kwargs']

        return self

    def to_dict(self):
        return {'module': self.module,
                'function': self.function,
                'classname': self.classname,
                'called_args': self.called_args,
                'called_kwargs': self.called_kwargs}

    def __call__(self, *args, **kwargs):

        if self.classname:
            assert(len(args) >= 1)
            obj = args[0]
            args = args[1:]

            if obj.__class__.__name__ != self.classname:
                raise CallableError(
                    "Callable is a class '%s' method but first arg is a '%s'"
                    % (self.classname, obj.__class__.__name__))

            if not hasattr(obj, self.function):
                raise CallableError(
                    ("Callable reference is invalid, class '%s' "
                     "has no method '%s'")
                    % (self.classname, self.function))

            func = getattr(obj, self.function)
        else:
            try:
                mod = importlib.import_module(self.module)
                func = mod.__dict__[self.function]
            except ImportError:
                raise CallableError(
                    ("Callable reference is invalid, could not "
                     "import module <%s>")
                    % self.module)
            except KeyError:
                raise CallableError(
                    "Callable reference is invalid, could not find function "
                    "<%s> in module <%s>"
                    % (self.function, self.module))

        args = self.called_args or args
        kwargs = self.called_kwargs or kwargs
        return func(*args, **kwargs)


class CallableField(PickledObjectField):
    """Model field which stores a Callable object."""

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if isinstance(value, Callable):
            return value

        value = super(CallableField, self).to_python(value)
        if value is not None:
            return Callable.from_dict(value)
        else:
            return None

    def get_prep_value(self, value):
        if value is not None:
            value = super(CallableField, self).get_prep_value(value.to_dict())
        return value


class Class(object):

    def __init__(self, cls=None):
        if cls:
            self.module = cls.__module__
            self.name = cls.__name__
        else:
            self.module = None
            self.name = None

    def __repr__(self):
        return "<Class %s:%s>" % (self.module, self.name)

    @classmethod
    def from_dict(cls, d):
        self = Class()

        self.module = d['module']
        self.name = d['name']

        return self

    def to_dict(self):
        return {'module': self.module,
                'name': self.name}

    def __call__(self, *args, **kwargs):
        try:
            mod = importlib.import_module(self.module)
            cls = mod.__dict__[self.name]
        except ImportError:
            raise ClassError(
                "Class reference is invalid, could not import module <%s>"
                % self.module)
        except KeyError:
            raise ClassError(
                "Class reference is invalid, could not find class "
                "<%s> in module <%s>"
                % (self.name, self.module))

        return cls(*args, **kwargs)


# See http://stackoverflow.com/questions/1110153/what-is-the-most-efficent-way-to-store-a-list-in-the-django-models
class SeparatedValuesField(models.TextField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token', ',')
        super(SeparatedValuesField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value: return
        if isinstance(value, list):
            return value
        return value.split(self.token)

    def get_prep_value(self, value):
        if not value: return
        assert(isinstance(value, list) or isinstance(value, tuple))
        return self.token.join([unicode(s) for s in value])

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)


def check_field_choice(model, field, value):
    field_choices = model._meta.get_field(field).choices
    try:
        return [c[0] for c in field_choices if value in c][0]
    except IndexError:
        raise IndexError("Invalid choice '%s' for field '%s'" % (value, field))


def field_choice_str(model, field, value):
    field_choices = model._meta.get_field(field).choices
    try:
        return [c[1] for c in field_choices if value == c[0]][0]
    except IndexError:
        raise IndexError("Invalid choice '%s' for field '%s'" % (value, field))
