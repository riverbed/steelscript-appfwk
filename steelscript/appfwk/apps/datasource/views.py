# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.http import Http404
from rest_framework.reverse import reverse
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAdminUser

from rest_framework_csv.renderers import CSVRenderer

from steelscript.appfwk.apps.datasource.forms import TableFieldForm
from steelscript.appfwk.apps.datasource.exceptions import JobCreationError
from steelscript.appfwk.apps.datasource import serializers
from steelscript.appfwk.apps.datasource.models import \
    Table, TableField, Column, Job


logger = logging.getLogger(__name__)


class DatasourceRoot(APIView):
    permission_classes = (IsAdminUser, )

    def get(self, request, format=None):
        return Response({
            'tables': reverse('table-list', request=request, format=format),
            'jobs': reverse('job-list', request=request, format=format),
        })


class TableList(generics.ListCreateAPIView):
    model = Table
    serializer_class = serializers.TableSerializer
    paginate_by = 20


class TableDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Table
    serializer_class = serializers.TableSerializer


class TableFieldList(generics.ListCreateAPIView):
    model = TableField
    serializer_class = serializers.TableFieldSerializer
    paginate_by = 20


class TableFieldDetail(generics.RetrieveUpdateDestroyAPIView):
    model = TableField
    serializer_class = serializers.TableFieldSerializer


class TableColumnList(generics.ListCreateAPIView):
    model = Column
    serializer_class = serializers.ColumnSerializer
    paginate_by = 20

    def get_queryset(self):
        """Filter results to specific table."""
        return Column.objects.filter(table=self.kwargs['pk'])


class TableJobList(APIView):
    """Create new jobs for a given table."""

    def get_queryset(self):
        """Filter results to specific table."""
        return Job.objects.filter(table=self.kwargs['pk'])

    def get_success_headers(self, job):
        # override method to return location of new job resource
        try:
            url = reverse('job-detail', args=(job.pk,), request=self.request)
            return {'Location': url}
        except (TypeError, KeyError):
            return {}

    def get(self, request, pk):
        """Return list of Job objects for given table."""
        job = self.get_queryset()
        serializer = serializers.JobSerializer(job, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Create new Job for the specified table using POSTed criteria."""
        table = Table.objects.get(pk=pk)
        all_fields = dict((f.keyword, f) for f in table.fields.all())

        # data needs to be not-None or form will be created as unbound
        data = self.request.POST or {}
        form = TableFieldForm(all_fields, use_widgets=False,
                              data=data)
        if form.is_valid(check_unknown=True):
            criteria = form.criteria()
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.create(table, criteria)
            job.start()
            serializer = serializers.JobSerializer(job, many=False)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=self.get_success_headers(job))
        except Exception as e:
            msg = 'Error processing Job: %s' % e.message
            raise JobCreationError(msg)


class ColumnList(generics.ListCreateAPIView):
    model = Column
    serializer_class = serializers.ColumnSerializer
    paginate_by = 20


class ColumnDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Column
    serializer_class = serializers.ColumnSerializer


class JobList(generics.ListAPIView):
    """List all Jobs in system.

    Creation of Jobs must be done via a TableJobList endpoint.
    """
    model = Job
    serializer_class = serializers.JobListSerializer
    paginate_by = 10

    def post_save(self, obj, created=False):
        if created:
            obj.start()


class JobDetail(generics.RetrieveAPIView):
    model = Job
    serializer_class = serializers.JobSerializer


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
