# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pandas
from django.db import models

from steelscript.appfwk.apps.metrics.models import Metric, STATUS_CHOICES
from steelscript.appfwk.apps.plugins import Plugin, register


logger = logging.getLogger(__name__)


class MetricsPlugin(Plugin):
    title = 'Example Metrics Plugin'
    description = 'Plugin demonstrating how to utilize and extend metrics'
    version = '0.1'
    author = 'Riverbed Technology'

    enabled = True
    can_disable = True

    reports = ['reports']
    libraries = ['libs']


register(MetricsPlugin)


#
# Custom Metrics - All code below goes in plugin models.py
#
def status_text(metric, status):
    """Create a consolidated status string for JS formatter.

    Takes a Metric object and a ``status`` text string for input.
    """
    status_map = {
        None: 'gray',
        '': 'gray',
        'None': 'gray',
        'Operational': 'green',
        'Warning': 'yellow',
        'Critical': 'red'
    }

    color = status_map[status]

    nodes = metric.affected_nodes.all()
    if len(nodes):
        infotext = '(%d)' % len(nodes)
    else:
        infotext = ''

    tooltip = '<br>'.join([n.name for n in nodes])

    return '%s:%s:%s' % (color, infotext, tooltip)


class NodeBase(models.Model):
    class Meta:
        abstract = True

    name = models.CharField(primary_key=True, max_length=100)

    STATUS_CHOICES = ('Up', 'Down')

    def __unicode__(self):
        return "<%s %s>" % (self.__class__, self.name)

    def __repr__(self):
        return unicode(self)


class ServiceNode(NodeBase):
    # link these nodes to ServicesMetric
    service = models.ForeignKey('ServicesMetric',
                                related_name='affected_nodes')


class ServicesMetric(Metric):
    schema = 'services'

    status_choices = ('N/A', 'Operational', 'Warning', 'Critical')

    # transient fields for receiving node status
    node_name = models.CharField(max_length=50, null=True, blank=True)
    node_status = models.CharField(max_length=20, null=True, blank=True,
                                   choices=zip(NodeBase.STATUS_CHOICES,
                                               NodeBase.STATUS_CHOICES))

    def process_data(self, data):
        """Update internal nodes list based on incoming message."""
        logger.debug('processing incoming data (%s) against instance %s' %
                     (data, self))

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

    @classmethod
    def _get_dataframe(cls):
        """Return a dataframe of table data, used by datasource query."""

        metrics = ServicesMetric.objects.all().order_by('id')

        columns = ('name', 'status_text')

        # if any nodes down status is 'Warning', otherwise 'Operational'
        data = []
        for m in metrics:
            nodes = m.affected_nodes.all()
            status = 'Warning' if len(nodes) > 0 else 'Operational'
            d = (m.name, status_text(m, m.override_value or status))
            data.append(d)

        # use 'data or None' to create empty df if no metrics avail
        df = pandas.DataFrame(data=data or None, columns=columns)
        return df


class NetworkNode(NodeBase):
    # link these nodes to NetworkMetric
    network = models.ForeignKey('NetworkMetric', related_name='affected_nodes')


class NetworkMetric(Metric):
    """
    This model will map a more complex metric with the following
    type of display:

    Location    Infra           LargeOffice
    --------    -----           -----------
    SFO         Critical (2)    Warning (1)
    BOS         Operational ()  Operational ()

    With these sets of stored data:

                    (parent_group1)   (parent_group2)
                    ---------------   -----------------
    (location1)     (parent_status)   (parent_status)
    (location2)     (parent_status)   (parent_status)

    Which maps to these rows of actual data:

    name            location    parent_group    parent_status   override_value
    ----            --------    ------------    -------------   --------------
    SFOInfra        SFO         Infra           Critical        None
    SFOLargeOffice  SFO         LargeOffice     Warning         None
    BOSInfra        BOS         Infra           Operational     None
    BOSLargeOffice  BOS         LargeOffice     Operational     None

    With associated NetworkNodes linked to each appropriate row.

    In order to keep unique primary keys, name gets saved as
    "%s%s" % (location, parent_group)

    Using a serializer that will process this incoming message:

    {
        "node_name": nodename,
        "node_status": "Down",
        "location": "SFO",
        "parent_group": "Infra",
        "parent_status": "Critical"
    }

    """

    schema = 'network'

    # this should be a Meta attr, but can't edit Meta as an abstract subclass
    unique_together = ('location', 'parent_group')

    # transient fields for receiving node status
    node_name = models.CharField(max_length=50, null=True, blank=True)
    node_status = models.CharField(max_length=20, null=True, blank=True,
                                   choices=zip(NodeBase.STATUS_CHOICES,
                                               NodeBase.STATUS_CHOICES))

    location = models.CharField(max_length=100, null=True, blank=True)
    parent_group = models.CharField(max_length=100, null=True, blank=True)
    parent_status = models.CharField(max_length=100, null=True, blank=True,
                                     choices=zip(STATUS_CHOICES,
                                                 STATUS_CHOICES))

    def save(self, *args, **kwargs):
        self.name = "%s%s" % (self.location, self.parent_group)
        super(NetworkMetric, self).save(*args, **kwargs)

    def process_data(self, data):
        """Update internal nodes list based on incoming message."""
        logger.debug('processing incoming data (%s) against instance %s' %
                     (data, self))

        # string input gets converted into list by field pre-processor
        # we extract what should be the first and only element
        new_node_name = data['node_name']

        # do we have this node recorded already?
        nodes = self.affected_nodes.filter(network=self, name=new_node_name)
        if nodes:
            node = self.affected_nodes.get(network=self, name=new_node_name)

            if data['node_status'].lower() == 'up':
                # if this was the last node, consider us operational
                if len(self.affected_nodes.all()) == 1:
                    self.parent_status = 'Operational'
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
                new_node = NetworkNode(name=new_node_name, network=self)
                new_node.save()
                logger.info('Added new down Network node %s' % new_node)

                if len(self.affected_nodes.all()) > 2:
                    # always go highest status when more than 3 nodes down
                    self.parent_status = STATUS_CHOICES[-1]
                else:
                    # Only update status if new status is higher
                    for status in STATUS_CHOICES[::-1]:
                        if self.parent_status == status:
                            break
                        elif data['parent_status'] == status:
                            self.parent_status = data['parent_status']

    @classmethod
    def _get_dataframe(cls):
        """Return a dataframe of table data, used by datasource query."""

        metrics = NetworkMetric.objects.all().order_by('id')

        columns = ('location', 'parent_group', 'status_text')
        data = [(m.location,
                 m.parent_group,
                 status_text(m, m.override_value or m.parent_status))
                for m in metrics]

        df = pandas.DataFrame(data=data or None, columns=columns)
        pdf = df.pivot(index='location',
                       columns='parent_group',
                       values='status_text').reset_index()

        # let's sort according to id in pivot table
        # ref http://stackoverflow.com/a/36965438/2157429
        df['order'] = df.index
        seq = df[['location', 'order']].to_dict(orient='records')
        ordering = {d['location']: d['order'] for d in seq}

        idx = pdf['location'].map(ordering).sort(inplace=False).index
        xdf = pdf.reindex(idx)

        return xdf

# get serializers registered with plugin models
import serializers
