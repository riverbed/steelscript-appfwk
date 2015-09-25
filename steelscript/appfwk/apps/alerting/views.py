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
from rest_framework.permissions import IsAdminUser

from steelscript.appfwk.apps.alerting import serializers
from steelscript.appfwk.apps.alerting.models import Alert, Event


logger = logging.getLogger(__name__)


class AlertingRoot(APIView):
    permission_classes = (IsAdminUser, )

    def get(self, request, format=None):
        return Response({
            'events': reverse('event-list', request=request, format=format),
            'alerts': reverse('alert-list', request=request, format=format),
        })


class AlertList(generics.ListAPIView):
    permission_classes = (IsAdminUser, )

    model = Alert
    serializer_class = serializers.AlertSerializer
    paginate_by = 20


class AlertDetail(generics.RetrieveAPIView):
    permission_classes = (IsAdminUser, )

    model = Alert
    serializer_class = serializers.AlertSerializer


class EventList(generics.ListAPIView):
    permission_classes = (IsAdminUser, )

    model = Event
    serializer_class = serializers.EventSerializer
    paginate_by = 20


class EventDetail(generics.RetrieveAPIView):
    permission_classes = (IsAdminUser, )

    model = Event
    serializer_class = serializers.EventSerializer


class EventLookup(generics.RetrieveAPIView):
    permission_classes = (IsAdminUser, )
    lookup_field = 'eventid'

    model = Event
    serializer_class = serializers.EventSerializer
