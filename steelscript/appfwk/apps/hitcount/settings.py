# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.conf import settings

# The minimum time between two counted visits (in minutes)
IGNORE_URLS = getattr(settings, 'IGNORE_URLS', [])
