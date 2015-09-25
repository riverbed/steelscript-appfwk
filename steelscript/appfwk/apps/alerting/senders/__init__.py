# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import absolute_import

from steelscript.appfwk.apps.alerting.senders.base import *
from steelscript.appfwk.apps.alerting.senders.snmp import *
from steelscript.appfwk.apps.alerting.senders.vm import *


def find_sender(name):
    return BaseSender.get_sender(name)
