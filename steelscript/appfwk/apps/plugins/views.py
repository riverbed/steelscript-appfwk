# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import json
import logging

from django.http import Http404, HttpResponse
from django.core import management
from django.core.management.base import CommandError
from django.contrib import messages
from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response

from steelscript.appfwk.apps.plugins import plugins
from steelscript.appfwk.apps.report.models import Report

logger = logging.getLogger(__name__)


def set_reports(namespace, enabled=False):
    reports = Report.objects.filter(namespace=namespace)
    reports.update(enabled=enabled)
    return [d['title'] for d in reports.values('title')]


class PluginsListView(APIView):
    """ Display list of installed plugins """

    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAdminUser,)

    def get(self, request):
        changed = request.QUERY_PARAMS.get('changed', False)

        return Response({'plugins': list(plugins.all()),
                         'changed': changed},
                        template_name='plugins_list.html')


class PluginsDetailView(APIView):
    """ Display detail of specific plugin """

    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAdminUser,)

    def get(self, request, slug, *args, **kwargs):
        try:
            plugin = plugins.get(slug)
        except KeyError:
            return Http404

        return Response({'plugin': plugin})

    def post(self, request, slug, *args, **kwargs):
        """ Enable or disable plugin - rest of details are read-only """

        try:
            plugin = plugins.get(slug)
        except KeyError:
            return Http404

        enabled = request.DATA.get('enabled', False)
        msgs = []
        # since we don't have helpful form cleaning, check for json 'false' too
        if (enabled == 'false' or enabled is False) and plugin.can_disable:
            plugin.enabled = False
            msgs.append('Plugin %s disabled.' % plugin.title)
            reports = set_reports(plugin.get_namespace(), False)
            for r in reports:
                msgs.append('Report %s disabled' % r)
        else:
            plugin.enabled = True
            msgs.append('Plugin %s enabled.' % plugin.title)
            reports = set_reports(plugin.get_namespace(), True)
            for r in reports:
                msgs.append('Report %s enabled' % r)

        for msg in msgs:
            messages.add_message(request._request, messages.INFO, msg)

        return HttpResponse(json.dumps({'plugin': plugin.__dict__}))


class PluginsCollectView(APIView):
    """ Collect reports for a specified plugin """

    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAdminUser,)

    def get(self, request, slug=None, *args, **kwargs):
        overwrite = request.QUERY_PARAMS.get('overwrite', False)
        if isinstance(overwrite, basestring) and overwrite.lower() == 'true':
            overwrite = True
        if slug is not None:
            try:
                plugin = plugins.get(slug)
            except KeyError:
                return Http404

            try:
                management.call_command('collectreports', plugin=slug,
                                        overwrite=overwrite)
                msg = ('Collected Reports for Plugin %s successfully.' %
                       plugin.title)
                messages.add_message(request._request, messages.INFO, msg)
            except CommandError as e:
                msg = ('Error collecting reports for %s - see log for details.'
                       % plugin.title)
                logger.debug(msg)
                logger.debug(e)
                messages.add_message(request._request, messages.ERROR, msg)
        else:
            try:
                management.call_command('collectreports', plugin=None,
                                        overwrite=overwrite)
                msg = 'Collected Reports for all plugins successfully.'
                messages.add_message(request._request, messages.INFO, msg)
            except CommandError as e:
                msg = ('Error collecting reports for one or more of the '
                       'plugins - see log for details.')
                logger.debug(msg)
                logger.debug(e)
                messages.add_message(request._request, messages.ERROR, msg)

        return HttpResponse(json.dumps(msg))
