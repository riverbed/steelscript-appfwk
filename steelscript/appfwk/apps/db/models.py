# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.db import models

from steelscript.appfwk.libs.fields import PickledObjectField


class ExistingIntervals(models.Model):
    """Store the existing time intervals in db for each table and
    a set of criteria fields (represented by the table_handle field).
    """
    namespace = models.CharField(max_length=20)

    sourcefile = models.CharField(max_length=200)

    table = models.CharField(max_length=50)

    criteria = PickledObjectField(null=True)

    table_handle = models.CharField(max_length=100, default="")

    intervals = PickledObjectField(null=True)

    tzinfo = PickledObjectField()
