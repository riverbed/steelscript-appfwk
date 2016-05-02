# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from django.conf import settings


# Helper function to determine whether URI should be ignored
# based on configured settings (under appfwk project).
# The comparison is a simple "startswith", so regexes are not supported.
def is_ignored(hitcount):
    is_ignored = False
    
    for ignored_url in getattr(settings, 'HITCOUNT_IGNORE_URLS', []):
        if hitcount.uri.startswith(ignored_url):
            is_ignored = True
            break

    return is_ignored
    

# Model Manager to add/update Hitcount objects
# in the event of a URI request.
class HitcountManager(models.Manager):
    def add_uri_visit(self, request, uri):
        hitcount_tuple = self.get_or_create(
            uri=uri
        )

        if hitcount_tuple and not is_ignored(hitcount_tuple[0]):
                hitcount_tuple[0].last_hit = now()
                hitcount_tuple[0].hits += 1
                hitcount_tuple[0].save()


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
