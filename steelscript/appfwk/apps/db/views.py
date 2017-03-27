# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from django.http import JsonResponse, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import views
from rest_framework.renderers import JSONRenderer

from steelscript.appfwk.apps.db import storage, ColumnFilter
from steelscript.common.timeutils import sec_string_to_datetime
from steelscript.appfwk.apps.db.models import ExistingIntervals
from steelscript.appfwk.apps.datasource.modules.ts_table import make_index
from steelscript.appfwk.apps.datasource.models import Table
from steelscript.appfwk.apps.datasource.models import Column

logger = logging.getLogger(__name__)


class Records(views.APIView):
    """View class of querying db"""

    rederer_classes = (JSONRenderer, )

    def get(self, request):

        # request is constructed as:
        # db/records?handle=**&start=**&end=**&timecol=**
        request_data = request.GET.dict()

        keys = ['handle', 'start']
        for k in keys:
            if k not in request_data:
                raise KeyError("Missing '%s' parameter in url" % k)

        handle = request_data['handle']
        try:
            obj = ExistingIntervals.objects.get(table_handle=handle)
        except ObjectDoesNotExist:
            msg = "Handle '{}' does not exist.".format(handle)
            return HttpResponseNotFound('<p>{}</p>'.format(msg))

        range = {}
        range['gte'] = sec_string_to_datetime(int(request_data['start']))
        if 'end' in request_data:
            range['lte'] = sec_string_to_datetime(int(request_data['end']))

        # Getting the time column name
        table = Table.from_ref(dict(sourcefile=obj.sourcefile,
                                    namespace=obj.namespace,
                                    name=obj.table))

        timecols = [c for c in table.get_columns(iskey=True)
                    if c.datatype == Column.DATATYPE_TIME]

        if not timecols:
            msg = "Table {} does not have a timeseries key column."\
                .format(obj.table)
            return HttpResponseNotFound('<p>{}</p>'.format(msg))

        time_col_name = timecols[0].name

        col_filters = [ColumnFilter(
                       query_type='range',
                       query={time_col_name: range})]

        records = storage.search(index=make_index(obj.namespace),
                                 doc_type=handle,
                                 col_filters=col_filters)

        return JsonResponse(records, safe=False)


class Handles(views.APIView):

    renderer_classes = (JSONRenderer, )

    def get(self, request):

        request_data = request.GET.dict()

        keys = ['namespace', 'table']
        for k, v in request_data.iteritems():
            if k not in keys:
                msg = "'{}' is not valid to query handles." .format(k)
                return HttpResponseNotFound('<p>{}</p>'.format(msg))

        res = []
        for obj in ExistingIntervals.objects.filter(**request_data):
            res.append(dict(handle=obj.table_handle,
                            criteria=str(obj.criteria),
                            namespace=obj.namespace,
                            sourcefile=obj.sourcefile,
                            table=obj.table,
                            intervals=str(obj.intervals)))
        return JsonResponse(res, safe=False)
