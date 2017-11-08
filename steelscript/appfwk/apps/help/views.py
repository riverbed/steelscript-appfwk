# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import sys
import ast
import json
import logging
import operator
import subprocess
from collections import OrderedDict

import pandas
from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer

from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.help.forms import NetProfilerInputForm, \
    NetSharkInputForm, AppResponseInputForm, AppResponseColumnsInputForm
from steelscript.appresponse.core._constants import report_sources, \
    report_source_to_groups

logger = logging.getLogger(__name__)


class SteelAbout(views.APIView):
    """View class of rendering `steel about` info"""
    permission_classes = (IsAuthenticated, )   # no guests
    renderer_classes = (TemplateHTMLRenderer, )

    # Titles for each section
    CORE_TITLE = 'Core packages:'
    APPFWK_TITLE = 'Application Framework packages:'
    REST_TITLE = 'REST tools and libraries:'
    SRC_PATH_TITLE = 'Paths to source:'
    PY_INFO_TITLE = 'Python information:'
    PLATFORM_TITLE = 'Platform information:'
    PY_PATH_TITLE = 'Python path:'

    PROVISIONED_TIME_FILE = '/etc/vagrant_last_provisioned'

    def _get_sys_info(self):
        """ Obtain the system info from the Environment (mostly a VM).
        :return: a dict containing system information
           (only provisioned time for now).
        """
        sys_info = OrderedDict()
        if os.path.exists(SteelAbout.PROVISIONED_TIME_FILE):
            with open(SteelAbout.PROVISIONED_TIME_FILE) as f:
                sys_info['Last Provisioned'] = f.read()
        return sys_info

    def _get_stdout(self):
        """Get the output of command `steel about`."""
        # find the executable
        steel = None

        if sys.prefix:
            ptest = os.path.join(sys.prefix, 'bin', 'steel')
            if os.path.exists(ptest):
                steel = ptest
        else:
            syspath = os.getenv('PATH').split(':')
            for path in syspath:
                if os.path.isdir(path) and 'steel' in os.listdir(path):
                    steel = os.path.join(path, 'steel')
                    break

        if steel is None:
            logger.error('"steel" command not found, searched the following '
                         'locations: %s, %s' % (sys.prefix, os.getenv('PATH')))

        p = subprocess.Popen([steel, 'about', '-v'], stdout=subprocess.PIPE)
        return p.communicate()[0]

    def _to_python(self, data):
        """Parse the output of `steel about` to python structures.

        There are 7 sections in the output, the data in the package
        and info sections will be stored as dicts, while the data
        in the section of source paths and python paths are stored
        as lists.

        :param string data: the output of `steel about`.

        :return: tuple of pkgs_and_info and paths
           pkgs_and_info is a dict keyed by titles of package and info
             sections with values as the data of each section;
           paths is a dict keyed by titles of source path and python path
             sections with values as the data of each section.
        """

        core_pkgs = OrderedDict()
        appfwk_pkgs = OrderedDict()
        rest_pkgs = OrderedDict()
        src_paths = []
        python_info = OrderedDict()
        platform_info = OrderedDict()
        python_path = None

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

        pkgs_and_info = OrderedDict()
        pkgs_and_info[SteelAbout.CORE_TITLE] = core_pkgs
        pkgs_and_info[SteelAbout.APPFWK_TITLE] = appfwk_pkgs
        pkgs_and_info[SteelAbout.REST_TITLE] = rest_pkgs
        pkgs_and_info[SteelAbout.PY_INFO_TITLE] = python_info
        pkgs_and_info[SteelAbout.PLATFORM_TITLE] = platform_info

        paths = OrderedDict()
        paths[SteelAbout.SRC_PATH_TITLE] = src_paths
        paths[SteelAbout.PY_PATH_TITLE] = python_path

        return pkgs_and_info, paths

    def get(self, request):
        sys_info = self._get_sys_info()
        data = self._get_stdout()
        pkgs_and_info, paths = self._to_python(data)

        return render_to_response('about.html',
                                  {'sys_info': sys_info,
                                   'dicts': pkgs_and_info,
                                   'lists': paths},
                                  context_instance=RequestContext(request))


class ColumnHelper(views.APIView):
    permission_classes = (IsAuthenticated, )   # no guests
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


class AppResponseHelper(views.APIView):
    permission_classes = (IsAuthenticated, )   # no guests
    renderer_classes = (TemplateHTMLRenderer, )

    def get(self, request, data_type):

        if data_type not in ['columns', 'sources']:
            raise Http404

        device = 'AppResponse'
        if data_type == 'columns':
            form = AppResponseColumnsInputForm()
        else:
            form = AppResponseInputForm()

        serialized_sources = json.dumps(report_sources)
        return render_to_response('help.html',
                                  {'device': device,
                                   'data_type': data_type,
                                   'report_sources': serialized_sources,
                                   'form': form,
                                   'results': None},
                                  context_instance=RequestContext(request))

    def post(self, request, data_type):

        if data_type not in ['columns', 'sources']:
            raise Http404
        device = 'AppResponse'
        if data_type == 'columns':
            form = AppResponseColumnsInputForm(request.POST)
        else:
            form = AppResponseInputForm(request.POST)

        results = None
        if form.is_valid():
            data = form.cleaned_data
            ar = DeviceManager.get_device(data['device'])

            if data_type == 'columns':
                rawcols = ar.reports.sources[data['source']]['columns']

                for col in rawcols.values():
                    if 'synthesized' in col:
                        synth = col['synthesized']
                        if isinstance(synth, dict):
                            col['synthesized'] = \
                                (', '.join(['{}: {}'.format(k, v)
                                 for k, v in synth.iteritems()]))

                colkeys = ['id', 'field', 'label', 'metric', 'type',
                           'unit', 'description', 'synthesized', 'grouped_by']
                coldf = pandas.DataFrame(rawcols.values(), columns=colkeys)
                coldf.fillna('---', inplace=True)
                coldf['iskey'] = coldf['grouped_by'].apply(
                    lambda x: True if x is True else '---')

                coldf.sort_values(by='id', inplace=True)
                results = list(coldf.to_records(index=False))
            else:
                colkeys = ['name', 'filters_on_metrics', 'granularities',
                           'groups']
                coldf = pandas.DataFrame(ar.reports.sources.values(),
                                         columns=colkeys)
                coldf['groups'] = coldf['name'].apply(
                    lambda x: ', '.join(report_source_to_groups[x]))
                coldf.sort_values(by='name', inplace=True)
                results = list(coldf.to_records(index=False))

        serialized_sources = json.dumps(report_sources)
        return render_to_response('help.html',
                                  {'device': device,
                                   'report_sources': serialized_sources,
                                   'data_type': data_type,
                                   'form': form,
                                   'results': results},
                                  context_instance=RequestContext(request))
