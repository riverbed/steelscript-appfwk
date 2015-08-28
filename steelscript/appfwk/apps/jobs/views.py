# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import logging

from django.http import Http404
from django.core import management
from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext

from rest_framework import generics, views
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework_csv.renderers import CSVRenderer

from steelscript.appfwk.apps.jobs.models import Job
from steelscript.appfwk.apps.jobs import serializers

logger = logging.getLogger(__name__)


class JobList(generics.ListAPIView):
    """List all Jobs in system.

    Creation of Jobs must be done via a TableJobList endpoint.
    """
    model = Job
    serializer_class = serializers.JobListSerializer
    paginate_by = 10
    permission_classes = (IsAdminUser,)

    def post_save(self, obj, created=False):
        if created:
            obj.start()


class JobVisualize(views.APIView):
    """Visualize jobs graphically."""
    renderer_classes = (TemplateHTMLRenderer,)
    permission_classes = (IsAdminUser,)

    def get(self, request):
        vizfile = 'job-graph.svg'
        vizpath = os.path.join(settings.MEDIA_ROOT, vizfile)

        if os.path.exists(vizpath):
            os.unlink(vizpath)

        logger.debug('Generating job visualization ...')
        management.call_command('jobtree',
                                outfile=vizpath)
        logger.debug('Visualization complete, file: %s' % vizpath)

        return render_to_response(
            'jobtree.html',
            {'svg_image': vizfile},
            context_instance=RequestContext(request)
        )


class JobDetail(generics.RetrieveAPIView):
    model = Job
    serializer_class = serializers.JobDetailSerializer


class JobDetailData(generics.RetrieveAPIView):
    model = Job
    serializer_class = serializers.JobDataSerializer
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
