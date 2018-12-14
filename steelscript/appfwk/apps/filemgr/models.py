# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from os import stat
import magic
import logging

from django.forms import ValidationError
from django.db import models
from django.db.models.fields.files import FieldFile
from steelscript.appfwk.apps.filemgr.filestore import file_store

logger = logging.getLogger(__name__)

class DataFileField(models.FileField):
    """ Implements a FileField with support for magic file type checking
        in the fields clean() method.
    """
    # The class to wrap instance attributes in. Accessing the file object off
    # the instance will always return an instance of attr_class.
    attr_class = FieldFile
    MAGIC_LEN = 1024
    SIG_LEN = 20

    def __init__(self, *args, **kwargs):
        self.magic_file_type = None
        super(DataFileField, self).__init__(*args, **kwargs)

    def clean(self, value, model_instance):
        self.magic_file_type = self.get_magic_type(value.file)

        if self.magic_file_type is not None:
            return super(DataFileField, self).clean(value, model_instance)
        else:
            raise ValidationError("Unable to determine file type.")

    @classmethod
    def get_magic_type(cls, file_object):
        file_object.seek(0)
        magic_code = magic.from_buffer(file_object.read(cls.MAGIC_LEN))
        file_object.seek(0)

        return magic_code


class DataFileBase(models.Model):

    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=255, blank=True)
    file_bytes = models.IntegerField(blank=True)

    def __unicode__(self):
        return self.description


class DataFile(DataFileBase):

    datafile = DataFileField(storage=file_store,
                             upload_to=file_store.location)

    def __unicode__(self):
        s = '{dfile}({f_type}) - {desc} (saved:{at})'
        return s.format(dfile=self.datafile,
                        desc=self.description,
                        at=self.uploaded_at,
                        f_type=self.file_type)

    def save(self, *args, **kwargs):
        self.file_type = self.datafile.field.magic_file_type
        self.file_bytes = self.datafile.file.size
        super(DataFile, self).save(*args, **kwargs)
