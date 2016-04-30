# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, views
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from steelscript.appfwk.apps.metrics.models import get_metric_map
from steelscript.appfwk.apps.metrics.serializers import find_serializer


logger = logging.getLogger(__name__)


class MetricDetail(views.APIView):
    """ Display and update user preferences
    """
    renderer_classes = (JSONRenderer,)
    permission_classes = (IsAdminUser,)

    def get(self, request, schema, metric_name):
        try:
            model = get_metric_map()[schema]
            serializer_cls = find_serializer(model, method='GET')
        except Exception as e:
            logger.error(e)
            raise Http404

        metric = get_object_or_404(model, name=metric_name)
        serializer = serializer_cls(instance=metric)
        data = serializer.data
        return Response(data)

    def post(self, request, schema):
        logger.debug('received metric post')
        try:
            model = get_metric_map()[schema]
            logger.debug('got model %s' % model)
            serializer_cls = find_serializer(model, method='POST')
            logger.debug('got serializer %s' % serializer_cls)
        except Exception as e:
            logger.error(e)
            raise Http404

        metric = get_object_or_404(model, name=request.DATA['name'])

        serialized = serializer_cls(instance=metric, data=request.DATA,
                                    context=request.DATA)
        if serialized.is_valid():
            serialized.save()

            return HttpResponse(status=200)
        else:
            logger.error('serialize error: %s' % serialized.errors)
            return HttpResponse(status=400)
