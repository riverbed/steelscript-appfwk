# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
from datetime import datetime
import magic
from django.forms import ValidationError
from django.db import models
from django.db.models.fields.files import FieldFile
from steelscript.appfwk.apps.pcapmgr.filestore import pcap_store

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

logger = logging.getLogger(__name__)


class PcapFileField(models.FileField):
    """ Implements a FileField with support for magic file type checking
        in the fields clean() method.
    """
    # The class to wrap instance attributes in. Accessing the file object off
    # the instance will always return an instance of attr_class.
    attr_class = FieldFile

    SUPPORTED_FILES = {'PCAP (libpcap format)': 'tcpdump capture file',
                       'PCAP Next Generation': 'pcap-ng capture file'}
    # Magic read length taken from magic.py examples:
    # https://github.com/ahupp/python-magic/blob/master/magic.py
    MAGIC_LEN = 1024
    SIG_LEN = 20

    def __init__(self, *args, **kwargs):
        self.magic_file_type = None
        super(PcapFileField, self).__init__(*args, **kwargs)

    def clean(self, value, model_instance):
        self.magic_file_type, file_type_name = self.get_magic_type(value.file)

        if self.magic_file_type is not None:
            return super(PcapFileField, self).clean(value, model_instance)
        else:
            raise ValidationError("File type '{0}' is not supported by this"
                                  " file manager.".format(file_type_name))

    @classmethod
    def get_magic_type(cls, file_object):
        file_object.seek(0)
        magic_code = magic.from_buffer(file_object.read(cls.MAGIC_LEN))
        file_object.seek(0)
        file_type_name = None
        for type_name, sig in cls.SUPPORTED_FILES.viewitems():
            if sig == magic_code[:cls.SIG_LEN]:
                file_type_name = type_name
                break

        return file_type_name, magic_code


class DataFileBase(models.Model):
    """ Base Data File model. Used as a base class by PCAPDataFile. Can
        be used as base class for other file store types.
    """
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return self.description


class PcapDataFile(DataFileBase):
    """ PCAP and PCAP NG supporting Data File model.
        Uses the PcapFileField and the PcapFileField.SUPPORTED_FILES in order
        to implement support for only the correct file types.
    """
    datafile = PcapFileField(storage=pcap_store,
                             upload_to=pcap_store.location)
    start_time = models.DateTimeField(default=datetime.now, blank=True)
    end_time = models.DateTimeField(default=datetime.now, blank=True)
    pkt_count = models.IntegerField(blank=True)
    packet_bytes = models.IntegerField(blank=True)

    SUPPORTED_FILES = PcapFileField.SUPPORTED_FILES

    def __unicode__(self):
        s = '{dfile}({f_type}) - {desc} (saved:{at})'
        return s.format(dfile=self.datafile,
                        desc=self.description,
                        at=self.uploaded_at,
                        f_type=self.file_type)

    def save(self, *args, **kwargs):
        """ Saved model instance to the database. 2 cases supported: 1st is
            UI created PcapDataFile instance with the datafile instance
            being a PcapFileField wrapped in a FieldFile. Second is a
            manually created PcapDataFile generated when a file system sync
            operation finds files not present in the DB."""

        # See attr_class variable for datafile instance for reason why
        # an instance variable is being checked for a class type variable.
        f_type = self.datafile.field.magic_file_type

        # This f_type variable will exist if this instance is a UI
        # created PCAPDataFile. But if this is being picked up via
        # a file system sync operation then it will not exist.
        if f_type:
            self.file_type = f_type
            datafile_clean = True
        else:
            # self.file_type was manually set during sync operation.
            # But the built in pseudo file object can't be used yet.
            datafile_clean = False

        if self.file_type in self.SUPPORTED_FILES:
            if datafile_clean:
                # UI created instance. Simply use the built in pseudo file type
                # object.
                pinfo = pcap_info(self.datafile.file)
            else:
                # Manually created during sync. Have to open as a true python
                # file object.
                with open(self.datafile.file.name, 'rb') as f:
                    pinfo = pcap_info(f)

            # Assign the special pcap fields.
            self.start_time = \
                datetime.utcfromtimestamp(pinfo['first_timestamp'])
            self.end_time = datetime.utcfromtimestamp(pinfo['last_timestamp'])
            self.pkt_count = pinfo['total_packets']
            self.packet_bytes = pinfo['total_bytes']

        super(PcapDataFile, self).save(*args, **kwargs)
