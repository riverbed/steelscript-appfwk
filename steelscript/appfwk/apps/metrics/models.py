# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.db import models


logger = logging.getLogger(__name__)


def get_metric_map():
    """Return mapping of schema to model classes."""
    classes = Metric.__subclasses__()
    return {c.schema: c for c in classes}


class Metric(models.Model):
    class Meta:
        abstract = True

    schema = None   # must be defined in subclasses
                    # used for url-routing

    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100, null=True, blank=True)
    override_value = models.CharField(max_length=100, null=True, blank=True)

    def __unicode__(self):
        return "<%s (%s) %s>" % (self.__class__.__name__,
                                 self.schema, self.name)

    def __repr__(self):
        return unicode(self)

    def process_data(self, data):
        """Base class to handle incoming data.

        ``data`` will be a dict of attributes
        """
        pass


#
# Custom Metrics - goes in plugin
#

class NetworkMetric(Metric):
    schema = 'network'

    parent_group = models.CharField(max_length=100, null=True, blank=True)
    parent_status = models.CharField(max_length=100, null=True, blank=True)


class ServiceNode(models.Model):
    name = models.CharField(primary_key=True, max_length=100)

    # list of node names
    service = models.ForeignKey('ServicesMetric', related_name='affected_nodes')

    def __unicode__(self):
        return "<ServiceNode %s>" % self.name

    def __repr__(self):
        return unicode(self)


class ServicesMetric(Metric):
    schema = 'services'

    # transient fields for receiving node status, for serializer validation
    node_name = models.CharField(max_length=50, null=True, blank=True)
    node_status = models.CharField(max_length=20, null=True, blank=True)

    def process_data(self, data):
        """Update internal nodes list based on incoming message."""
        logger.debug('processing incoming data against instance')

        # string input gets converted into list by field pre-processor
        # we extract what should be the first and only element
        new_node_name = data['node_name']

        # do we have this node recorded already?
        if self.affected_nodes.filter(service=self, name=new_node_name):
            node = self.affected_nodes.get(service=self, name=new_node_name)

            if data['node_status'].lower() == 'up':
                node.delete()
            else:
                # we've already logged this node being down
                logger.warning('Received metric update for Service node %s, '
                               'already recorded as down' % node)

        else:
            # we only store nodes marked down, ignore unknown 'up' nodes
            if data['node_status'].lower() == 'up':
                logger.warning('Received metric update for unknown '
                               'Service node %s, not previously recorded down'
                               % new_node_name)
            else:
                new_node = ServiceNode(name=new_node_name, service=self)
                new_node.save()
                logger.info('Added new down Service node %s' % new_node)
