# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import datetime
import threading

from django.db import models
from django.dispatch import Signal, receiver

from steelscript.common.timeutils import datetime_to_microseconds
from steelscript.appfwk.libs.fields import (PickledObjectField,
                                            FunctionField, Function)
from steelscript.appfwk.apps.alerting.routes import find_router
from steelscript.appfwk.apps.alerting.source import Source
from steelscript.appfwk.apps.alerting.caches import ModelCache

import logging
logger = logging.getLogger(__name__)


post_data_save = Signal(providing_args=['data', 'context'])
error_signal = Signal(providing_args=['context'])

lock = threading.Lock()


class TriggerCache(ModelCache):
    """Cache of Trigger objects."""
    _model = 'alerting.Trigger'
    _key = 'source'


class ErrorHandlerCache(ModelCache):
    """Cache of ErrorHandler objects."""
    _model = 'alerting.ErrorHandler'
    _key = 'source'


def create_event_id():
    """Return unique ID value for each triggered event."""
    # XXX microseconds should be sufficiently unique,
    #  but may need more if microseconds still cause event overlaps
    dt = datetime.datetime.now()
    return datetime_to_microseconds(dt)


class DestinationThread(threading.Thread):
    def __init__(self, destination, eventid, result, context,
                 is_error=False, **kwargs):
        self.destination = destination
        self.eventid = eventid
        self.result = result
        self.context = context
        self.is_error = is_error
        super(DestinationThread, self).__init__(**kwargs)

    def run(self):
        router = self.destination.get_router()

        if self.is_error:
            message_context = Source.error_context(self.context)
        else:
            message_context = Source.message_context(self.context, self.result)

        message = self.destination.get_message(message_context)

        alert = Alert(eventid=self.eventid,
                      level=router.level,
                      router=self.destination.router,
                      message=message,
                      options=self.destination.options,
                      context=self.context,
                      trigger_result=self.result)
        # need to save to get datetime assigned
        alert.save()
        logger.debug('Routing Alert %s via destination %s' %
                     (alert, self.destination))
        router.send(alert)


class TriggerThread(threading.Thread):
    def __init__(self, trigger, data, context, **kwargs):
        self.trigger = trigger
        self.data = data
        self.context = context
        super(TriggerThread, self).__init__(**kwargs)

    def start_router(self, result):
        destinations = self.trigger.destinations.all()
        eventid = create_event_id()
        for d in destinations:
            DestinationThread(d, eventid, result, self.context).start()

    def run(self):
        func = self.trigger.trigger_func

        logger.debug('Evaluating Trigger %s ...' % self.trigger.name)
        result = func(self.data, self.context)
        logger.debug('Trigger result: %s' % result)

        if result:
            if isinstance(result, (list, tuple)):
                for r in result:
                    self.start_router(r)
            else:
                self.start_router(result)


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
    eventid = create_event_id()
    for h in handlers:
        DestinationThread(h.destination, eventid, None,
                          context, is_error=True).start()


#
# Models
#


class Alert(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    eventid = models.BigIntegerField()
    level = models.CharField(max_length=50)
    router = models.CharField(max_length=100)
    options = PickledObjectField(blank=True, null=True)
    message = models.TextField()
    context = PickledObjectField()
    trigger_result = PickledObjectField()

    def __unicode__(self):
        msg = self.message
        if len(msg) > 20:
            msg = '%s...' % msg[:20]
        return '<Alert %s/%d (%s) %s/%s>' % (self.id or 'X',
                                             self.eventid,
                                             self.router,
                                             self.level, msg)

    def __repr__(self):
        return unicode(self)

    def get_details(self):
        """Return details in a string"""
        msg = []
        fmt = '{0:15}: {1}'
        msg.append(fmt.format('ID', self.id))
        msg.append(fmt.format('EventID', self.eventid))
        msg.append(fmt.format('Timestamp', self.timestamp))
        msg.append(fmt.format('Level', self.level))
        msg.append(fmt.format('Router', self.router))
        msg.append(fmt.format('Dest options', self.options))
        msg.append(fmt.format('Message', self.message))
        msg.append(fmt.format('Trigger Result', self.trigger_result))
        msg.append(fmt.format('Context', self.context))
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
        tfunc = Function(trigger_func, params=params)
        t = Trigger(name=kwargs.pop('name', Source.name(source)),
                    source=Source.encode(source),
                    trigger_func=tfunc,
                    **kwargs)
        t.save()
        return t

    def add_destination(self, router, options=None,
                        template=None, template_func=None):
        """Assign route to the given Trigger."""
        r = Destination.create(router=router,
                               options=options,
                               template=template,
                               template_func=template_func)
        self.destinations.add(r)

    def add_error_handler(self, router, options=None,
                          template=None, template_func=None):
        """Convenience method to create error handler for same source."""
        e = ErrorHandler.create(name=self.name + 'ErrorHandler',
                                source=self.source,
                                router=router,
                                options=options,
                                template=template,
                                template_func=template_func)
        return e


class Destination(models.Model):
    name = models.CharField(max_length=100)
    router = models.CharField(max_length=100)
    options = PickledObjectField(blank=True, null=True)
    template = models.TextField(blank=True, null=True)
    template_func = FunctionField(null=True)

    def __unicode__(self):
        if self.options:
            return '<Destination %d/%s -> %s>' % (self.id, self.router,
                                                  str(self.options))
        else:
            return '<Destination %d/%s>' % (self.id, self.router)

    def save(self, *args, **kwargs):
        if self.template is None and self.template_func is None:
            msg = ('Missing template or template_func definition in '
                   'Destination creation for Destination %s' % self)
            raise AttributeError(msg)
        super(Destination, self).save()

    @classmethod
    def create(cls, router, options=None, template=None,
               template_func=None):
        r = Destination(router=router,
                        options=options,
                        template=template,
                        template_func=template_func)
        r.save()
        return r

    def get_router(self):
        """Return instance of Router associated with the model.
        """
        return find_router(self.router)()

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
    def create(cls, name, source, router, options=None,
               template=None, template_func=None):
        """Create new ErrorHandler and its associated Destination."""
        destination = Destination.create(router, options,
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
