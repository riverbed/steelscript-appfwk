# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import views
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from steelscript.appfwk.apps.metrics.models import get_schema_map
from steelscript.appfwk.apps.metrics.serializers import find_serializer


logger = logging.getLogger(__name__)


class MetricDetail(views.APIView):
    """ Display and update user preferences
    """
    renderer_classes = (JSONRenderer,)
    permission_classes = (IsAdminUser,)

    def get_kwargs(self, model, request):
        """Return kwargs to use for finding specific model instance."""
        # define the method of looking up the model instance
        # default is to use name as primary key
        if hasattr(model, 'unique_together'):
            # but if the model identifies alternate keys, use those
            fields = model.unique_together
            get_kwargs = {f: request.DATA[f] for f in fields}
        else:
            get_kwargs = {'name': request.DATA['name']}
        return get_kwargs

    def get(self, request, schema, metric_name):
        try:
            model = get_schema_map()[schema]
            serializer_cls = find_serializer(model, method='GET')
        except Exception as e:
            logger.error(e)
            raise Http404

        metric = get_object_or_404(model, name=metric_name)
        serializer = serializer_cls(instance=metric)
        data = serializer.data
        return Response(data)

    def post(self, request, schema):
        logger.debug('Received metric POST for schema %s' % schema)
        try:
            model = get_schema_map()[schema]
            get_kwargs = self.get_kwargs(model, request)
            serializer_cls = find_serializer(model, method='POST')
        except Exception as e:
            logger.error(e)
            raise Http404

        metric = get_object_or_404(model, **get_kwargs)

        serialized = serializer_cls(instance=metric, data=request.DATA,
                                    context=request.DATA)
        if serialized.is_valid():
            serialized.save()

            return HttpResponse(status=200)
        else:
            logger.error('serialize error: %s' % serialized.errors)
            return HttpResponse(status=400)
