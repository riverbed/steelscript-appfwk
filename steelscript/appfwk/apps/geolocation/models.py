# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.db import models

import logging
logger = logging.getLogger(__name__)


#######################################################################
#
# Locations
#

class Location(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __unicode__(self):
        return self.name


class LocationIP(models.Model):
    location = models.ForeignKey(Location)
    address = models.GenericIPAddressField()
    mask = models.GenericIPAddressField()
