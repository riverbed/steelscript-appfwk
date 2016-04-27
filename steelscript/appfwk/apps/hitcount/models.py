# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.db import models
from django.utils.translation import ugettext_lazy as _
from steelscript.appfwk.apps.hitcount import settings


try:
    from django.utils.timezone import now
except ImportError:
    from datetime import datetime
    now = datetime.now

def is_ignored (request, _hitcount):
    is_ignored = False
    
    for ignored_url in settings.IGNORE_URLS:
        if request.META["PATH_INFO"].startswith(ignored_url):
            is_ignored = True
            break

    return is_ignored
    

class HitcountManager(models.Manager):
    def add_uri_visit(self, request, uri):
        hitcount = self.get_or_create(
            uri=uri
        )

        if len(hitcount):
            if not is_ignored(request, hitcount[0]):
                hitcount[0].last_hit = now()
                hitcount[0].hits += 1
                hitcount[0].save()


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
