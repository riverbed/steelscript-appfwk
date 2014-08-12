# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import datetime
import threading
from collections import defaultdict

from django.db import models
from django.dispatch import Signal, receiver
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from steelscript.common.timeutils import datetime_to_microseconds
from steelscript.appfwk.libs.fields import (PickledObjectField,
                                            FunctionField, Function)

from steelscript.appfwk.apps.alerting.routes import find_router
from steelscript.appfwk.apps.alerting.source import Source

import logging
logger = logging.getLogger(__name__)


post_data_save = Signal(providing_args=['data', 'context'])

lock = threading.Lock()


class TriggerCache(object):
    """Provide quick lookup operation for Triggers by source attribute.

    Since source is stored as a PickledObjectField, direct filtering
    using query logic won't be reliable, and since the encoding/decoding
    could be expensive across each Trigger all the time, this class
    pre-caches the values for quicker evaluation.

    This is an in-memory cache and will be re-populated on server
    restarts or cold-calling a run table operation.
    """
    _lookup = None

    @classmethod
    def _get(cls):
        lock.acquire()
        if cls._lookup is None:
            logger.debug('TriggerCache: loading new data')
            cls._lookup = defaultdict(list)
            triggers = Trigger.objects.select_related()
            for t in triggers:
                logger.debug('TriggerCache: adding %s to key %s' % (t, t.source))
                cls._lookup[t.source].append(t)
        lock.release()

    @classmethod
    def clear(cls):
        logger.debug('TriggerCache: clearing cache')
        cls._lookup = None

    @classmethod
    def filter(cls, value):
        logger.debug('TriggerCache: filtering on %s' % value)
        if cls._lookup is None:
            cls._get()
        return cls._lookup[Source.encode(value)]


class RouteThread(threading.Thread):
    def __init__(self, route, eventid, result, context, **kwargs):
        self.route = route
        self.eventid = eventid
        self.result = result
        self.context = context
        super(RouteThread, self).__init__(**kwargs)

    def run(self):
        router = self.route.get_router()
        message_context = Source.message_context(self.context, self.result)
        message = self.route.get_message(message_context)
        alert = Alert(eventid=self.eventid,
                      level=router.level,
                      router=self.route.router,
                      message=message,
                      destination=self.route.destination,
                      context=self.context,
                      trigger_result=self.result)
        # need to save to get datetime set
        alert.save()
        logger.debug('Routing Alert %s via router %s' %
                     (alert, self.route))
        router.send(alert)


class TriggerThread(threading.Thread):
    def __init__(self, trigger, data, context, **kwargs):
        self.trigger = trigger
        self.data = data
        self.context = context
        super(TriggerThread, self).__init__(**kwargs)

    def get_event_id(self):
        """Return unique ID value for each triggered event."""
        # XXX microseconds should be sufficiently unique,
        #  but may need more if microseconds still cause event overlaps
        dt = datetime.datetime.now()
        return datetime_to_microseconds(dt)

    def start_router(self, result):
        routes = self.trigger.routes.all()
        eventid = self.get_event_id()
        for route in routes:
            RouteThread(route, eventid, result, self.context).start()

    def run(self):
        func = self.trigger.trigger_func

        logger.debug('Evaluating Trigger %s ...' % self.trigger.name)
        #from IPython import embed; embed()
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
    data = kwargs.pop('data', None)
    context = kwargs.pop('context', None)
    # xxx data may not be a dataframe
    logger.debug('Received post_data_save signal from %s with df size %s '
                 'and context %s' %
                 (sender, data.shape, Source.get(context)))

    triggers = TriggerCache.filter(Source.get(context))
    logger.debug('Found %d triggers.' % len(triggers))
    for t in triggers:
        TriggerThread(t, data, context).start()


#
# Models
#


class Alert(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    eventid = models.IntegerField()
    level = models.CharField(max_length=50)
    router = models.CharField(max_length=100)
    destination = PickledObjectField()
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

    def get_details(self):
        """Return details in a string"""
        msg = []
        fmt = '{0:15}: {1}'
        msg.append(fmt.format('ID', self.id))
        msg.append(fmt.format('EventID', self.eventid))
        msg.append(fmt.format('Timestamp', self.timestamp))
        msg.append(fmt.format('Level', self.level))
        msg.append(fmt.format('Router', self.router))
        msg.append(fmt.format('Destination', self.destination))
        msg.append(fmt.format('Message', self.message))
        msg.append(fmt.format('Trigger Result', self.trigger_result))
        msg.append(fmt.format('Context', self.context))
        return '\n'.join(msg)


class Trigger(models.Model):
    name = models.CharField(max_length=100)
    source = PickledObjectField()
    trigger_func = FunctionField()
    routes = models.ManyToManyField('Route', null=True)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = 'trigger_' + hash(self.source)
        super(Trigger, self).save(*args, **kwargs)
        TriggerCache.clear()

    def delete(self, *args, **kwargs):
        TriggerCache.clear()
        super(Trigger, self).delete(*args, **kwargs)

    @classmethod
    def create(cls, source, trigger_func, **kwargs):
        tfunc = Function(trigger_func)
        t = Trigger(name=kwargs.pop('name', Source.name(source)),
                    source=Source.encode(source),
                    trigger_func=tfunc,
                    **kwargs)
        t.save()
        return t

    def add_route(self, router, destination,
                  template=None, template_func=None):
        r = Route.create(router=router,
                         destination=destination,
                         template=template,
                         template_func=template_func)
        self.routes.add(r)


class Route(models.Model):
    name = models.CharField(max_length=100)
    router = models.CharField(max_length=100)
    destination = PickledObjectField()
    template = models.TextField(blank=True, null=True)
    template_func = FunctionField(null=True)

    def __unicode__(self):
        return '<Route %d/%s -> %s>' % (self.id, self.router,
                                        str(self.destination))

    def save(self, *args, **kwargs):
        if self.template is None and self.template_func is None:
            raise AttributeError('Missing template or template_func '
                                 'definition in Route creation for Route %s'
                                 % self)
        super(Route, self).save()

    @classmethod
    def create(cls, router, destination, template=None,
               template_func=None):
        r = Route(router=router,
                  destination=destination,
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


create_trigger = Trigger.create
create_route = Route.create
