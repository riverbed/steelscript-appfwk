# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import magic
from datetime import datetime
from django.forms import ValidationError
from steelscript.appfwk.libs.packets import pcap_info
from django.db import models
from django.db.models.fields.files import FieldFile
from steelscript.appfwk.apps.pcapmgr.filestore import PCAPStore, SystemStore

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
        if len(mft):
            self.magic_file_type = mft[0]

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


class DataFile(DataFileBase):
    """ Records for a file maintained in local storage.
    """
    datafile = models.FileField(storage=SystemStore,
                                upload_to='/media/documents/')

    def __unicode__(self):
        s = '{dfile}({type}) - {desc} (saved:{at})'
        return s.format(dfile=self.datafile,
                        desc=self.description,
                        at=self.uploaded_at,
                        type=self.file_type)

    def save(self, *args, **kwargs):
        self.file_type = "Not Available"
        super(DataFile, self).save(*args, **kwargs)


class PcapDataFile(DataFileBase):
    SUPPORTED_FILES = PcapFileField.SUPPORTED_FILES
    datafile = PcapFileField(storage=PCAPStore,
                             upload_to='/media/pcap/')
    start_time = models.DateTimeField(default=datetime.now, blank=True)
    end_time = models.DateTimeField(default=datetime.now, blank=True)
    pkt_count = models.IntegerField(blank=True)

    def __unicode__(self):
        s = '{dfile}({type}) - {desc} (saved:{at})'
        return s.format(dfile=self.datafile,
                        desc=self.description,
                        at=self.uploaded_at,
                        type=self.file_type)

    def save(self, *args, **kwargs):
        self.file_type = self.datafile.field.magic_file_type
        pinfo = pcap_info(self.datafile.file)
        self.start_time = datetime.utcfromtimestamp(pinfo[0])
        self.end_time = datetime.utcfromtimestamp(pinfo[1])
        self.pkt_count = pinfo[2]
        super(PcapDataFile, self).save(*args, **kwargs)
