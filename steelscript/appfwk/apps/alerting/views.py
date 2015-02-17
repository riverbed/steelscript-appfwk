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

from rest_framework_csv.renderers import CSVRenderer

from steelscript.appfwk.apps.alerting import serializers
from steelscript.appfwk.apps.alerting.models import Alert, Event


logger = logging.getLogger(__name__)


class AlertingRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'events': reverse('event-list', request=request, format=format),
            'alerts': reverse('alert-list', request=request, format=format),
        })


class AlertList(generics.ListAPIView):
    model = Alert
    serializer_class = serializers.AlertSerializer
    paginate_by = 20


class AlertDetail(generics.RetrieveAPIView):
    model = Alert
    serializer_class = serializers.AlertSerializer


class EventList(generics.ListAPIView):
    model = Event
    serializer_class = serializers.EventSerializer
    paginate_by = 20


class EventDetail(generics.RetrieveAPIView):
    model = Event
    serializer_class = serializers.EventSerializer
