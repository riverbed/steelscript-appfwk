# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from steelscript.appfwk.apps.hitcount.models import Hitcount


# NOTE on ignored URLs:
# Ignored URLs are specified in appfwk's (local_)settings.py
#  under "HITCOUNT_INGORE_URLS".
# They will be collected, but have 'hits' set to 0.
# There are at least two options for displaying only Targeted
#  (= non-ignored) URL hits:
# - Option #1: Override get_queryset() in custom HitcountAdmin
#               to show only nonzero-hit entries.
# - Option #2: Add filter to separate hit entries into
#               Targeted/Ignored/All (treating Targeted as default).


# Create custom list filter that filters out ignored URLs by default.
class HitcountIgnoreListFilter(admin.SimpleListFilter):
    title           = _('tracking status')
    parameter_name  = 'hits'

    def lookups(self, request, model_admin):
        # Default value of 'None' gets mapped to 'Not Ignored'.
        # Also need to add in explicit 'All'.
        return (
            (None, _('Tracked')),
            ('ignored', _('Ignored')),
            ('all', _('All')),
        )

    # Rewrite this method to _NOT_ force 'selected' to be text,
    # since now None is one of the choices explicitly added above.
    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() == None:
            # Filter to show entries with non-zero hit counts (= tracked).
            return queryset.filter(hits__gt=0)
        elif self.value() == 'ignored':
            # Filter to show ignored entries (hits=0).
            return queryset.filter(hits=0)
        else:
            # For "All", just show everything.
            return queryset


class HitcountAdmin(admin.ModelAdmin):
    list_display = ['uri', 'hits', 'last_hit']
    # <Disabled> Option #2:
    #list_filter = [HitcountIgnoreListFilter]
    search_fields = ['uri']

    # Option #1:
    # Override to show only Tracked hits.
    def get_queryset(self, request):
        qs = super(HitcountAdmin, self).get_queryset(request)
        return qs.filter(hits__gt=0)

admin.site.register(Hitcount, HitcountAdmin)
