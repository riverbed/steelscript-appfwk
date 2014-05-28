# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import operator
import logging

from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from rest_framework import views
from rest_framework.renderers import TemplateHTMLRenderer

from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.help.forms import NetProfilerInputForm, NetSharkInputForm


logger = logging.getLogger(__name__)


class ColumnHelper(views.APIView):
    renderer_classes = (TemplateHTMLRenderer, )

    def get(self, request, device_type):
        if device_type == 'netprofiler':
            device = 'NetProfiler'
            form = NetProfilerInputForm()
        elif device_type == 'netshark':
            device = 'NetShark'
            form = NetSharkInputForm()
        else:
            raise Http404

        return render_to_response('help.html',
                                  {'device': device,
                                   'form': form,
                                   'results': None},
                                  context_instance=RequestContext(request))

    def post(self, request, device_type):
        if device_type == 'netprofiler':
            device = 'NetProfiler'
            form = NetProfilerInputForm(request.POST)
        elif device_type == 'netshark':
            device = 'NetShark'
            form = NetSharkInputForm(request.POST)
        else:
            raise Http404

        results = None
        if form.is_valid():
            data = form.cleaned_data
            if device_type == 'netprofiler':
                profiler = DeviceManager.get_device(data['device'])

                results = profiler.search_columns(realms=[data['realm']],
                                                  centricities=[data['centricity']],
                                                  groupbys=[data['groupby']])
                results.sort(key=operator.attrgetter('key'))
                results.sort(key=operator.attrgetter('iskey'), reverse=True)
                results = [(c.iskey, c.key, c.label, c.id) for c in results]
            elif device_type == 'netshark':
                shark = DeviceManager.get_device(data['device'])

                results = [(f.id, f.description, f.type) for f in shark.get_extractor_fields()]
                results.sort(key=operator.itemgetter(0))

        return render_to_response('help.html',
                                  {'device': device,
                                   'form': form,
                                   'results': results},
                                  context_instance=RequestContext(request))
