# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.core.files.storage import FileSystemStorage

SystemStore = FileSystemStorage(location='/media/documents/',
                                base_url='/media/documents/')
PCAPStore = FileSystemStorage(location='/media/pcap/',
                              base_url='/media/pcap/')
