# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.http import Http404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework_csv.renderers import CSVRenderer

from steelscript.appfwk.apps.jobs.models import Job
from steelscript.appfwk.apps.jobs.serializers import JobListSerializer, \
    JobSerializer, JobDataSerializer

logger = logging.getLogger(__name__)


class JobList(generics.ListAPIView):
    """List all Jobs in system.

    Creation of Jobs must be done via a TableJobList endpoint.
    """
    model = Job
    serializer_class = JobListSerializer
    paginate_by = 10

    def post_save(self, obj, created=False):
        if created:
            obj.start()


class JobDetail(generics.RetrieveAPIView):
    model = Job
    serializer_class = JobSerializer


class JobDetailData(generics.RetrieveAPIView):
    model = Job
    serializer_class = JobDataSerializer
    renderer_classes = (JSONRenderer, CSVRenderer, )

    def get(self, request, *args, **kwargs):
        job = self.get_object()
        base_filename = (request.QUERY_PARAMS.get('filename', None) or
                         job.table.name)

        df = job.data()

        # normalize time column to user timezone
        if 'time' in df:
            tz = request.user.timezone
            df = df.set_index('time').tz_convert(tz).reset_index()

        if request.accepted_renderer.format == 'csv':
            content_type = 'text/csv'
            filename = base_filename + '.csv'

            # use nicer column labels for CSV, and in the correct order
            columns = job.get_columns()
            request.accepted_renderer.headers = [col.label for col in columns]

            # map the label names to data source columns
            names = dict((col.name, col.label) for col in columns)
            df.rename(columns=lambda c: names.get(c, c), inplace=True)

        elif request.accepted_renderer.format == 'json':
            content_type = 'application/json'
            filename = base_filename + '.json'

        else:
            # chances are we won't get here because the DRF
            # content negotiation will have already failed
            msg = 'Invalid format requested.'
            logging.debug(msg)
            raise Http404(msg)

        headers = {'Content-Disposition': 'attachment; filename=%s' % filename}
        response = Response(df.to_dict('records'),
                            content_type=content_type,
                            headers=headers)

        return response
