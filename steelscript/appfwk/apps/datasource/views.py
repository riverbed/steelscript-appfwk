# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from rest_framework.reverse import reverse
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser


from steelscript.appfwk.apps.datasource.forms import TableFieldForm
from steelscript.appfwk.apps.jobs.exceptions import JobCreationError
from steelscript.appfwk.apps.datasource import serializers
from steelscript.appfwk.apps.datasource.models import \
    Table, TableField, Column
from steelscript.appfwk.apps.jobs.models import Job
from steelscript.appfwk.apps.jobs.serializers import JobSerializer


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
        serializer = JobSerializer(job, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Create new Job for the specified table using POSTed criteria."""
        table = Table.objects.get(pk=pk)
        all_fields = dict((f.keyword, f) for f in table.fields.all())

        # data needs to be not-None or form will be created as unbound
        data = self.request.POST or {}
        form = TableFieldForm(all_fields, use_widgets=False,
                              include_hidden=True, data=data)
        if form.is_valid(check_unknown=True):
            criteria = form.criteria()
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.create(table, criteria)
            job.start()
            serializer = JobSerializer(job, many=False)
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
