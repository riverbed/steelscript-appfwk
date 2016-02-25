# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import ast

import operator
import logging
import subprocess


from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from rest_framework import views
from rest_framework.renderers import TemplateHTMLRenderer
from collections import OrderedDict

from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.help.forms import NetProfilerInputForm, NetSharkInputForm


logger = logging.getLogger(__name__)


class SteelAbout(views.APIView):
    """View class of rendering `steel about` info"""
    renderer_classes = (TemplateHTMLRenderer, )

    # Titles for each section
    CORE_TITLE = 'Core packages:'
    APPFWK_TITLE = 'Application Framework packages:'
    REST_TITLE = 'REST tools and libraries:'
    SRC_PATH_TITLE = 'Paths to source:'
    PY_INFO_TITLE = 'Python information:'
    PLATFORM_TITLE = 'Platform information:'
    PY_PATH_TITLE = 'Python path:'

    def get(self, request):

        core_pkgs = OrderedDict()
        appfwk_pkgs = OrderedDict()
        rest_pkgs = OrderedDict()
        src_paths = []
        python_info = OrderedDict()
        platform_info = OrderedDict()
        python_path = None

        p = subprocess.Popen(['/home/vagrant/virtualenv/bin/steel',
                              'about', '-v'],
                             stdout=subprocess.PIPE)

        data = p.communicate()[0]

        lines = data.split('\n')

        src_paths_idx = lines.index(SteelAbout.SRC_PATH_TITLE)
        python_info_idx = lines.index(SteelAbout.PY_INFO_TITLE)
        platform_info_idx = lines.index(SteelAbout.PLATFORM_TITLE)
        python_path_idx = lines.index(SteelAbout.PY_PATH_TITLE)

        # Parse each line into corresponding containers
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            if line.startswith('steelscript') and 'appfwk' not in line:
                [name, version] = line.split()
                core_pkgs[name] = version
            elif line.startswith('steelscript.appfwk'):
                [name, version] = line.split()
                appfwk_pkgs[name] = version
            elif line.startswith('reschema') or line.startswith('sleepwalker'):
                [name, version] = line.split()
                rest_pkgs[name] = version
            elif idx > src_paths_idx and idx < python_info_idx:
                # the line is a path to source
                src_paths.append(line)
            elif idx > python_info_idx and idx < platform_info_idx:
                # the line is about python information as 'key  : value'
                [k, v] = [x.strip() for x in line.split(':', 1)]
                python_info[k] = v
            elif idx > platform_info_idx and idx < python_path_idx:
                # the line is about platform information as 'key : value'
                [k, v] = [x.strip() for x in line.split(':', 1)]
                platform_info[k] = v
            elif idx == python_path_idx + 1:
                python_path = ast.literal_eval(line)

        dicts = OrderedDict()
        dicts[SteelAbout.CORE_TITLE] = core_pkgs
        dicts[SteelAbout.APPFWK_TITLE] = appfwk_pkgs
        dicts[SteelAbout.REST_TITLE] = rest_pkgs
        dicts[SteelAbout.PY_INFO_TITLE] = python_info
        dicts[SteelAbout.PLATFORM_TITLE] = platform_info

        lists = OrderedDict()
        lists[SteelAbout.SRC_PATH_TITLE] = src_paths
        lists[SteelAbout.PY_PATH_TITLE] = python_path

        return render_to_response('about.html',
                                  {'dicts': dicts, 'lists': lists},
                                  context_instance=RequestContext(request))


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
