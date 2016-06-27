# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
from collections import defaultdict

from rest_framework import serializers


logger = logging.getLogger(__name__)


SERIALIZER_MAP = defaultdict(dict)


def register_serializer(s, method='*'):
    """Add mapping of serializer `s` to associated model.

    Optionally specify associated method, (GET, POST, PUT, DELETE).  If not
    specified, will insert global mapping for all http methods.
    """
    global SERIALIZER_MAP
    SERIALIZER_MAP[s.Meta.model].update({method.lower(): s})


def find_serializer(m, method):
    """Given model `m` return associated serializer for given method.

    If '*' mapping included, will return that for any given method requested.
    """
    mapping = SERIALIZER_MAP[m]
    if '*' in mapping:
        return mapping['*']
    else:
        return mapping[method.lower()]


class BaseMetricSerializer(serializers.ModelSerializer):

    def restore_object(self, attrs, instance=None):
        """
        Handle how incoming data should be mapped into a model instance.
        """
        instance = (super(BaseMetricSerializer, self)
                    .restore_object(attrs, instance=instance))

        if instance is not None:
            logger.debug('processing with instance method')
            instance.process_data(attrs)

        return instance

    def save_object(self, obj, **kwargs):
        return super(BaseMetricSerializer, self).save_object(obj, **kwargs)
