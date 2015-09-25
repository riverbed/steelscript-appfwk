# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import copy


class Source(object):
    """Encapsulate access and encoding of source data objects.

    This class acts as a bridging API from source data to the
    Alerting module.
    """
    # make this subclassable somehow ...
    # possibly via abstract base class (import abc)

    @staticmethod
    def get(context):
        """Get source object from a given source context."""
        return context['job'].table

    @staticmethod
    def message_context(context, result):
        """Get key-value context to pass to message format string."""
        # XXX: can't use "actual_criteria" here because it hasn't yet
        # been saved to Job on the main thread
        d = context['job'].criteria

        # pull data from result dict, check if its a dict itself
        # and flatten it into message_context
        r = copy.deepcopy(result)
        data = r.pop('data', None)
        if hasattr(data, 'keys'):
            d.update(data)
        else:
            d['result'] = data

        d.update(r)
        return d

    @staticmethod
    def error_context(context):
        """Extract error message from alert context."""
        j = context['job']
        d = j.criteria
        d['id'] = j.id
        d['message'] = j.message
        d['status'] = j.status
        return d

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
