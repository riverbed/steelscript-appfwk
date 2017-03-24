# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import views
from rest_framework.renderers import JSONRenderer

from steelscript.appfwk.apps.db import storage, ColumnFilter
from steelscript.common.timeutils import sec_string_to_datetime
from steelscript.appfwk.apps.db.models import ExistingIntervals
from steelscript.appfwk.apps.datasource.modules.ts_table import make_index

logger = logging.getLogger(__name__)


class Records(views.APIView):
    """View class of querying db"""

    rederer_classes = (JSONRenderer, )

    def get(self, request):

        # request is constructed as:
        # db/records?handle=**&start=**&end=**&timecol=**
        request_data = request.GET.dict()

        keys = ['handle', 'start', 'end', 'timecol']
        for k in keys:
            if k not in request_data:
                raise KeyError("Missing '%s' parameter in url" % k)

        handle = request_data['handle']
        try:
            res = ExistingIntervals.objects.get(table_handle=handle)
        except ObjectDoesNotExist:
            raise KeyError("Handle '{}' does not exist.".format(handle))

        start_time = sec_string_to_datetime(int(request_data['start']))
        end_time = sec_string_to_datetime(int(request_data['end']))

        time_col = request_data['timecol']
        col_filters = [ColumnFilter(
                       query_type='range',
                       query={time_col: {'gte': start_time,
                                         'lte': end_time}})]

        records = storage.search(index=make_index(res.plugin),
                                 doc_type=handle,
                                 col_filters=col_filters)

        return JsonResponse(records, safe=False)


class Handles(views.APIView):

    renderer_classes = (JSONRenderer, )

    def get(self, request):

        res = []
        for obj in ExistingIntervals.objects.all():
            res.append(dict(handle=obj.table_handle,
                            cirteria=str(obj.criteria),
                            plugin=obj.plugin,
                            table=obj.table,
                            intervals=str(obj.intervals)))
        return JsonResponse(res, safe=False)
