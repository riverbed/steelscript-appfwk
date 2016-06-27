# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pytz
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            timezone.activate(request.user.timezone)
        elif settings.GUEST_USER_ENABLED:
            tz = settings.GUEST_USER_TIME_ZONE
            timezone.activate(pytz.timezone(tz))
        else:
            logger.debug('GUEST ACCESS DISABLED, using default timezone')
