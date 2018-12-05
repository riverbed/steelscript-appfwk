# Copyright (c) 2018 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.db import models
from ordered_model.models import OrderedModel

from steelscript.appfwk.apps.report.models import Report

logger = logging.getLogger(__name__)


class Workflow(models.Model):
    """Sequence of Reports to execute as part of a Runbook"""

    title = models.CharField(max_length=50)
    steps = models.ManyToManyField(Report, through='Sequence')

    def __str__(self):
        return self.title


class Sequence(OrderedModel):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    order_with_respect_to = 'workflow'

    class Meta:
        ordering = ('workflow', 'order')

    def __str__(self):
        return '{}/{}-{}'.format(self.workflow, self.order, self.report.title)
