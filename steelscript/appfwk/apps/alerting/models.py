# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import threading
from collections import defaultdict

from django.db import models
from django.dispatch import Signal, receiver
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from steelscript.appfwk.libs.fields import (PickledObjectField,
                                            FunctionField, Function)

from steelscript.appfwk.apps.alerting.routes import find_routers

import logging
logger = logging.getLogger(__name__)


post_data_save = Signal(providing_args=['data', 'context'])


class TriggerCache(object):
    """Provide quick lookup operation for Triggers by source attribute.

    Since source is stored as a PickledObjectField, direct filtering
    using query logic won't be reliable, and since the encoding/decoding
    could be expensive across each Trigger all the time, this class
    pre-caches the values for quicker evaluation.
    """
    _lookup = None

    @classmethod
    def _get(cls):
        logger.debug('TriggerCache: loading new data')
        cls._lookup = defaultdict(list)
        triggers = Trigger.objects.select_related()
        for t in triggers:
            logger.debug('TriggerCache: adding %s to key %s' % (t, t.source))
            cls._lookup[t.source].append(t)

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
    def __init__(self, route, result, context, **kwargs):
        self.route = route
        self.result = result
        self.context = context
        super(RouteThread, self).__init__(**kwargs)

    def run(self):
        # create alert and send it before saving to db to
        router = self.route.get_router_class()()
        message = self.route.get_message(self.context)
        alert = Alert(level=router.level,
                      router=self.route.router,
                      message=message,
                      context=self.context)
        logger.debug('Routing Alert %s via router %s' %
                     (alert, self.route))
        router.send(alert)
        alert.save()


class TriggerThread(threading.Thread):
    def __init__(self, trigger, data, context, **kwargs):
        self.trigger = trigger
        self.data = data
        self.context = context
        super(TriggerThread, self).__init__(**kwargs)

    def run(self):
        func = self.trigger.trigger_func

        logger.debug('Evaluating Trigger %s ...' % self.trigger.name)
        #from IPython import embed; embed()
        result = func(self.data, self.context)
        logger.debug('Trigger result: %s' % result)
        if result:
            routes = self.trigger.routes.all()
            for route in routes:
                # XXX update context
                RouteThread(route, result, self.context).start()


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


class Source(object):
    """Encapsulate access and encoding of source data objects.
    """
    # make this subclassable somehow ...
    # possibly via abstract base class (import abc)

    @staticmethod
    def get(context):
        """Get source object from a given context."""
        return context['job'].table

    @staticmethod
    def name(source):
        """Instead of hashable, return description from given value."""
        return 'trigger_%s-%s' % (source.name, source.sourcefile)

    @staticmethod
    def encode(source):
        """Normalize source values to hashable type for lookups."""
        # require a hashable object, see here for simple way to hash dicts:
        # http://stackoverflow.com/a/16162138/2157429
        from steelscript.appfwk.apps.datasource.models import Table
        return frozenset(Table.to_ref(source).itervalues())


class Alert(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    level = models.CharField(max_length=50)
    router = models.CharField(max_length=100)
    message = models.TextField()
    context = PickledObjectField()

    def __unicode__(self):
        msg = self.message
        if len(msg) > 10:
            msg = '%s...' % msg[:10]
        return '<Alert %s (%s) %s/%s>' % (self.id or 'X', self.router,
                                          self.level, msg)


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
    destination = models.CharField(max_length=200)
    template = models.TextField(blank=True, null=True)
    template_func = FunctionField(null=True)

    def __unicode__(self):
        return '<Route %d/%s -> %s>' % (self.id, self.router, self.destination)

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

    def get_router_class(self):
        """Return instance of Router associated with the model.
        """
        routers = find_routers()
        for r in routers:
            if self.router == r.__name__:
                return r

    def get_message(self, context):
        """Return string from either template_func or template
        afer processed with given context.
        """
        if self.template_func:
            return self.template_func(**context)
        else:
            return self.template.format(**context)


create_trigger = Trigger.create
create_route = Route.create
