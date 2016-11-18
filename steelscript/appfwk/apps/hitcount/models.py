# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import re
import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from django.conf import settings

from steelscript.appfwk.project.locks import ClassLock, TransactionLock

logger = logging.getLogger(__name__)


# Helper function to determine whether URI should be ignored
# based on configured settings (under appfwk project).
HITCOUNT_IGNORE_REGEX = re.compile(
    '|'.join(getattr(settings, 'HITCOUNT_IGNORE_URLS', []))
)


def is_ignored(url):
    return True if HITCOUNT_IGNORE_REGEX.search(url) else False


# Model Manager to add/update Hitcount objects
# in the event of a URI request.
class HitcountManager(models.Manager):
    def add_uri_visit(self, request, uri):

        # only create objects and score for desired URLs
        if not is_ignored(uri):
            # lock down the table
            with ClassLock('checking for uri'):
                hitcount, created = self.select_for_update().get_or_create(
                    uri=uri
                )

            # If this request comes from a cache,
            # it may include a custom field: Obj-Cache-Hits.
            # This field stores a temporary hit count (as string),
            # which should be added to the running total.
            cache_hits_str = request.META.get('HTTP_OBJ_CACHE_HITS', '0')
            try:
                cache_hits = int(cache_hits_str)
            except (TypeError, ValueError):
                cache_hits = 0

            hitcount_increment = cache_hits + 1

            with TransactionLock(hitcount, 'updating count'):
                # Update hitcount object for this URI.
                hitcount.last_hit = now()
                hitcount.hits += hitcount_increment
                hitcount.save()


# Model that maps hits and visit time to unique URIs requested.
class Hitcount(models.Model):
    uri = models.CharField(max_length=255, blank=True, null=True)
    last_hit = models.DateTimeField(blank=True, null=True)
    hits = models.IntegerField(default=0)

    objects = HitcountManager()

    def __unicode__(self):
        return self.uri

    class Meta:
        ordering = ['uri']
        verbose_name = _('hit')
        verbose_name_plural = _('hits')
