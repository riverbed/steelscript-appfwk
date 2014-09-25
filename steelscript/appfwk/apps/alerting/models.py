# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import itertools
import threading

from django.db import models
from django.dispatch import Signal, receiver
from django_extensions.db.fields import UUIDField

from steelscript.appfwk.libs.fields import (PickledObjectField,
                                            FunctionField, Function)
from steelscript.appfwk.apps.alerting.senders import find_sender
from steelscript.appfwk.apps.alerting.source import Source
from steelscript.appfwk.apps.alerting.caches import ModelCache

import logging
logger = logging.getLogger(__name__)


post_data_save = Signal(providing_args=['data', 'context'])
error_signal = Signal(providing_args=['context'])

lock = threading.Lock()

DEFAULT_SEVERITY = 0    # Default severity when none assigned from trigger
ERROR_SEVERITY = 99     # Severity assigned to all errors


class TriggerCache(ModelCache):
    """Cache of Trigger objects."""
    _model = 'alerting.Trigger'
    _key = 'source'


class ErrorHandlerCache(ModelCache):
    """Cache of ErrorHandler objects."""
    _model = 'alerting.ErrorHandler'
    _key = 'source'


class Results(object):
    """Container data structure for trigger method results.

    Stores data in an internal list of dicts.  The keys for each
    dict must be consistent - once the initial data gets stored all
    further data additions must use the same set of keys.

    The 'severity' key is optional, and leaving it blank will default it
    to the integer 0.

    When adding data or initializing the object, data may be a list
    of objects.  The supporting keys may also be lists, but they must
    be of the same length as the data.  Alternately, the keys may
    be single-values, in which case that value will be applied to
    all elements of the data list.

    >>> r = Results()
    >>> r.add_data([42, 88], foo=19)
    >>> r.get_data()
    [{'data': 42, 'foo': 19, 'severity': 0},
     {'data': 88, 'foo': 19, 'severity': 0}]
    """
    def __init__(self, data=None, severity=None, **kwargs):
        self._keys = None
        self._data = []
        if data:
            self.add_data(data, severity=severity, **kwargs)

    def __len__(self):
        return len(self._data)

    def _add_items(self, **kwargs):
        try:
            kvs = zip(*[[(k, v) for v in val] for k, val in kwargs.items()])
            items = map(dict, kvs)
        except TypeError:
            # single values rather than lists
            items = [dict([(k, v) for k, v in kwargs.items()])]
        self._data.extend(items)

    def add_data(self, data, severity=None, **kwargs):
        keys = set(['severity'] + kwargs.keys())
        if self._keys is None:
            self._keys = keys

        if keys - self._keys:
            msg = 'Invalid keys passed to add_data: %s' % (keys - self._keys)
            raise ValueError(msg)
        elif self._keys - keys:
            msg = 'Missing data keys in add_data: %s' % (self._keys - keys)
            raise ValueError(msg)

        if severity is None:
            severity = DEFAULT_SEVERITY
        kwargs['severity'] = severity

        if isinstance(data, (list, tuple)):
            attrs = {}
            for k in self._keys:
                if isinstance(kwargs[k], (list, tuple)):
                    if len(data) != len(kwargs[k]):
                        msg = 'Length of %s does not match length of data' % k
                        raise ValueError(msg)
                    attrs[k] = kwargs[k]
                else:
                    attrs[k] = itertools.repeat(kwargs[k], len(data))
            self._add_items(data=data, **attrs)
        else:
            self._add_items(data=data, **kwargs)

    def get_data(self):
        return self._data


class DestinationThread(threading.Thread):
    def __init__(self, destination, event,
                 is_error=False, **kwargs):
        self.destination = destination
        self.event = event
        self.is_error = is_error
        super(DestinationThread, self).__init__(**kwargs)

    def run(self):
        sender = self.destination.get_sender()

        if self.is_error:
            level = 'error'  # can be overridden by options, but not Sender
            message_context = Source.error_context(self.event.context)
        else:
            level = None    # set via options or Sender
            message_context = Source.message_context(self.event.context,
                                                     self.event.trigger_result)

        message = self.destination.get_message(message_context)
        options = self.destination.options
        if options:
            level = self.destination.options.get('level', None)

        alert = Alert(event=self.event,
                      level=level or sender.level,
                      sender=self.destination.sender,
                      message=message,
                      options=options)
        # need to save to get datetime assigned
        alert.save()
        logger.debug('Sending Alert %s via Destination %s' %
                     (alert, self.destination))
        sender.send(alert)


class TriggerThread(threading.Thread):
    def __init__(self, trigger, data, context, **kwargs):
        self.trigger = trigger
        self.data = data
        self.context = context
        super(TriggerThread, self).__init__(**kwargs)

    def start_destinations(self, result):
        destinations = self.trigger.destinations.all()
        severity = result.pop('severity')
        event = Event(severity=severity,
                      context=self.context,
                      trigger_result=result)
        event.save()
        logger.debug('New Event created: %s' % event)
        for d in destinations:
            DestinationThread(d, event).start()

    def run(self):
        func = self.trigger.trigger_func

        logger.debug('Evaluating Trigger %s ...' % self.trigger.name)
        result = func(self.data, self.context)

        for r in result.get_data():
            logger.debug('Trigger result: %s' % result)
            self.start_destinations(r)


@receiver(post_data_save, dispatch_uid='post_data_receiver')
def process_data(sender, **kwargs):
    data = kwargs.pop('data')
    context = kwargs.pop('context')
    source = Source.get(context)

    # xxx data may not be a dataframe
    logger.debug('Received post_data_save signal from %s with df size %s '
                 'and context %s' %
                 (sender, data.shape, context))

    triggers = TriggerCache.filter(Source.encode(source))
    logger.debug('Found %d triggers.' % len(triggers))
    for t in triggers:
        TriggerThread(t, data, context).start()


@receiver(error_signal, dispatch_uid='error_signal_receiver')
def process_error(sender, **kwargs):
    context = kwargs.pop('context')
    source = Source.get(context)

    logger.debug('Received error_signal from %s with context %s' %
                 (sender, context))

    handlers = ErrorHandlerCache.filter(Source.encode(source))
    logger.debug('Found %d handlers.' % len(handlers))
    event = Event(severity=ERROR_SEVERITY, context=context,
                  trigger_result=None)
    event.save()
    logger.debug('New Event created: %s' % event)
    for h in handlers:
        DestinationThread(h.destination, event, is_error=True).start()


#
# Models
#
class Event(models.Model):
    """Event instance which may result in one or more Alerts."""
    timestamp = models.DateTimeField(auto_now=True)
    eventid = UUIDField()
    severity = models.IntegerField()
    log_message = models.TextField(null=True, blank=True)
    context = PickledObjectField()
    trigger_result = PickledObjectField()

    def __unicode__(self):
        return '<Event %s/%s (%s)>' % (self.id, self.eventid, self.timestamp)

    def __repr__(self):
        return unicode(self)

    def get_details(self):
        """Return details in a string"""
        msg = []
        fmt = '{0:15}: {1}'
        msg.append(fmt.format('ID', self.id))
        msg.append(fmt.format('EventID', self.eventid))
        msg.append(fmt.format('Severity', self.severity))
        msg.append(fmt.format('Timestamp', self.timestamp))
        msg.append(fmt.format('Log Message', self.log_message))
        msg.append(fmt.format('Trigger Result', self.trigger_result))
        msg.append(fmt.format('Context', self.context))

        alerts = self.alert_set.all()
        if alerts:
            msg.append('')
            msg.append('Associated Alerts:')
            for a in alerts:
                msg.append(a.get_details())
        return '\n'.join(msg)


class Alert(models.Model):
    """Individual notification sent by a Sender for a specific Event."""
    timestamp = models.DateTimeField(auto_now=True)
    event = models.ForeignKey('Event')
    level = models.CharField(max_length=50)
    sender = models.CharField(max_length=100)
    options = PickledObjectField(blank=True, null=True)
    message = models.TextField()

    def __unicode__(self):
        msg = self.message
        if len(msg) > 20:
            msg = '%s...' % msg[:20]
        return '<Alert %s (%s/%s)>' % (self.id or 'X',
                                       self.sender, msg)

    def __repr__(self):
        return unicode(self)

    def get_details(self):
        """Return details in a string"""
        msg = []
        fmt = '{0:15}: {1}'
        msg.append(fmt.format('ID', self.id))
        msg.append(fmt.format('EventID', self.event.eventid))
        msg.append(fmt.format('Timestamp', self.timestamp))
        msg.append(fmt.format('Level', self.level))
        msg.append(fmt.format('Sender', self.sender))
        msg.append(fmt.format('Dest options', self.options))
        msg.append(fmt.format('Message', self.message))
        return '\n'.join(msg)


class Trigger(models.Model):
    name = models.CharField(max_length=100)
    source = PickledObjectField()
    trigger_func = FunctionField()
    destinations = models.ManyToManyField('Destination', null=True)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = 'trigger_' + hash(self.source)
        super(Trigger, self).save(*args, **kwargs)
        TriggerCache.clear()

    def delete(self, *args, **kwargs):
        TriggerCache.clear()
        super(Trigger, self).delete(*args, **kwargs)

    @classmethod
    def create(cls, source, trigger_func, params=None, **kwargs):
        """Create trigger against given source table.

        :param table source: Table object reference
        :param function trigger_func: function object to run for trigger
        :param dict params: optional additional parameters to pass to
            trigger_func
        """
        tfunc = Function(trigger_func, params=params)
        t = Trigger(name=kwargs.pop('name', Source.name(source)),
                    source=Source.encode(source),
                    trigger_func=tfunc,
                    **kwargs)
        t.save()
        return t

    def add_destination(self, sender, options=None,
                        template=None, template_func=None):
        """Assign destination to the given Trigger.

        :param str sender: name of sender class to use
        :param dict options: optional dictionary of attributes
        :param str template: format string to use for resulting alert
        :param function template_func: optional function which returns a
            formatted string, receives same context as template
        """
        r = Destination.create(sender=sender,
                               options=options,
                               template=template,
                               template_func=template_func)
        self.destinations.add(r)

    def add_error_handler(self, sender, options=None,
                          template=None, template_func=None):
        """Convenience method to create error handler for same source."""
        e = ErrorHandler.create(name=self.name + 'ErrorHandler',
                                source=self.source,
                                sender=sender,
                                options=options,
                                template=template,
                                template_func=template_func)
        return e


class Destination(models.Model):
    name = models.CharField(max_length=100)
    sender = models.CharField(max_length=100)
    options = PickledObjectField(blank=True, null=True)
    template = models.TextField(blank=True, null=True)
    template_func = FunctionField(null=True)

    def __unicode__(self):
        if self.options:
            return '<Destination %d/%s -> %s>' % (self.id, self.sender,
                                                  str(self.options))
        else:
            return '<Destination %d/%s>' % (self.id, self.sender)

    def save(self, *args, **kwargs):
        if self.template is None and self.template_func is None:
            msg = ('Missing template or template_func definition in '
                   'Destination creation for Destination %s' % self)
            raise AttributeError(msg)
        super(Destination, self).save()

    @classmethod
    def create(cls, sender, options=None, template=None,
               template_func=None):
        r = Destination(sender=sender,
                        options=options,
                        template=template,
                        template_func=template_func)
        r.save()
        return r

    def get_sender(self):
        """Return instance of Sender associated with the model.
        """
        return find_sender(self.sender)()

    def get_message(self, context):
        """Return string from either template_func or template
        processed with result and given context.
        """
        if self.template_func:
            return self.template_func(**context)
        else:
            return self.template.format(**context)


class ErrorHandler(models.Model):
    """Special alert which bypasses triggers and gets immediately routed.

    The template/template_func attributes need to be provided to create
    an associated Destination object, and only one Destination can be defined
    per ErrorHandler.

    One ErrorHandler should be defined for each desired route.

    """
    name = models.CharField(max_length=100)
    source = PickledObjectField()
    destination = models.ForeignKey('Destination')

    def __unicode__(self):
        return '<ErrorHandler %d/%s>' % (self.id, self.name)

    @classmethod
    def create(cls, name, source, sender, options=None,
               template=None, template_func=None):
        """Create new ErrorHandler and its associated Destination."""
        destination = Destination.create(sender, options,
                                         template, template_func)

        # when called via Trigger classmethod source has already been encoded
        if not isinstance(source, frozenset):
            source = Source.encode(source)

        e = ErrorHandler(name=name, source=source, destination=destination)
        e.save()
        return e


create_trigger = Trigger.create
create_destination = Destination.create
create_error_handler = ErrorHandler.create
