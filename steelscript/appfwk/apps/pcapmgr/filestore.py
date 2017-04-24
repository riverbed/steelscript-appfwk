# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
from django.conf import settings
from django.core.files.storage import FileSystemStorage

if not hasattr(settings, 'PCAP_STORE'):
    raise ValueError('Please set local_settings.PCAP_STORE to the proper '
                     'path for pcap storage')

pcap_store = FileSystemStorage(location='{0}/'.format(settings.PCAP_STORE),
                               base_url='{0}/'.format(settings.PCAP_STORE))
