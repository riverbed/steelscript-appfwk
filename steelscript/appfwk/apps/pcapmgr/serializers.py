# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from rest_framework import serializers

from steelscript.appfwk.apps.pcapmgr.models import DataFile, PcapDataFile


class DataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFile


class PcapDataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PcapDataFile
