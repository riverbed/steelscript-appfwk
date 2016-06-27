# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pandas

from django.db import models


logger = logging.getLogger(__name__)


STATUS_CHOICES = ('Operational', 'Warning', 'Critical')


def get_schema_map():
    """Return mapping of schema to model classes."""
    classes = Metric.__subclasses__()
    return {c.schema: c for c in classes}


def get_metric_map():
    """Return mapping of model names to model classes."""
    classes = Metric.__subclasses__()
    return {c.__name__: c for c in classes}


class MetricManager(models.Manager):

    def get_dataframe(self):
        """Return a dataframe of table data, used by datasource query."""

        # if we have created a custom get_dataframe, use that
        if hasattr(self.model, '_get_dataframe'):
            return self.model._get_dataframe()

        # otherwise use the default implementation
        metrics = self.all()

        columns = ('name', 'value')
        data = [(m.name, m.override_value or m.value) for m in metrics]
        df = pandas.DataFrame(data=data or None, columns=columns)

        return df


class Metric(models.Model):
    objects = MetricManager()

    class Meta:
        abstract = True

    schema = None   # must be defined in subclasses, used for url-routing

    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100, null=True, blank=True)
    override_value = models.CharField(max_length=100, null=True, blank=True,
                                      choices=zip(STATUS_CHOICES,
                                                  STATUS_CHOICES))

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
