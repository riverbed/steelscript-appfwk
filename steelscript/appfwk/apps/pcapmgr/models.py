# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import magic
from django.conf import settings
from datetime import datetime
from django.forms import ValidationError
from django.db import models
from django.db.models.fields.files import FieldFile
from steelscript.appfwk.apps.pcapmgr.filestore import PCAPStore

WARN_PCAP = True
try:
    from steelscript.packets.core.pcap import pcap_info
    WARN_PCAP = False
except ImportError:
    def pcap_info(file_handle):
        return {'first_timestamp': 0.0,
                'last_timestamp': 0.0,
                'total_packets': 0,
                'total_bytes': 0}

if not hasattr(settings, 'PCAP_STORE'):
    raise ValueError('Please set local_settings.PCAP_STORE to the proper '
                     'path for pcap storage')

logger = logging.getLogger(__name__)


class PcapFileField(models.FileField):
    attr_class = FieldFile
    SUPPORTED_FILES = {'pcap': {'sig': 'tcpdump capture file',
                                'name': 'PCAP (libpcap format)'},
                       'pcapng': {'sig': 'pcap-ng capture file',
                                  'name': "PCAP Next Generation"}}

    # Magic read length taken from magic.py examples:
    # https://github.com/ahupp/python-magic/blob/master/magic.py
    MAGIC_LEN = 1024
    SIG_LEN = 20

    def __init__(self, *args, **kwargs):
        self.magic_file_type = None
        super(PcapFileField, self).__init__(*args, **kwargs)

    def clean(self, value, model_instance):
        magic_type = magic.from_buffer(value.file.read(min(self.MAGIC_LEN,
                                                           value.file.size)))
        value.file.seek(0)

        mft = [x['name'] for x in self.SUPPORTED_FILES.values() if
               x['sig'] == magic_type[:self.SIG_LEN]]
        if mft:
            self.magic_file_type = mft[0]
        else:
            self.magic_file_type = "__Unsupported File Type__"

        if self.magic_file_type is not None:
            return super(PcapFileField, self).clean(value, model_instance)
        else:
            raise ValidationError("File type '{0}' is not supported by this"
                                  " file manager.".format(magic_type))


class DataFileBase(models.Model):
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return self.description


class PcapDataFile(DataFileBase):
    SUPPORTED_FILES = PcapFileField.SUPPORTED_FILES
    pcap_warning = WARN_PCAP
    datafile = PcapFileField(storage=PCAPStore,
                             upload_to='{0}/'.format(settings.PCAP_STORE))
    start_time = models.DateTimeField(default=datetime.now, blank=True)
    end_time = models.DateTimeField(default=datetime.now, blank=True)
    pkt_count = models.IntegerField(blank=True)
    packet_bytes = models.IntegerField(blank=True)

    def __unicode__(self):
        s = '{dfile}({type}) - {desc} (saved:{at})'
        return s.format(dfile=self.datafile,
                        desc=self.description,
                        at=self.uploaded_at,
                        type=self.file_type)

    def save(self, *args, **kwargs):
        self.file_type = self.datafile.field.magic_file_type
        if self.file_type in (x['name'] for x in
                              self.SUPPORTED_FILES.values()):
            pinfo = pcap_info(self.datafile.file)
            self.start_time = \
                datetime.utcfromtimestamp(pinfo['first_timestamp'])
            self.end_time = datetime.utcfromtimestamp(pinfo['last_timestamp'])
            self.pkt_count = pinfo['total_packets']
            self.packet_bytes = pinfo['total_bytes']
        else:
            self.start_time = datetime.now()
            self.end_time = datetime.now()
            self.pkt_count = 0
            self.packet_bytes = 0
        super(PcapDataFile, self).save(*args, **kwargs)
