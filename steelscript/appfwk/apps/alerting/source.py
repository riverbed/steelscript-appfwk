# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


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
        if hasattr(result, 'keys'):
            d.update(result)
        else:
            d['result'] = result
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
