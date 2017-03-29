# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import logging

from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import generics, views
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from steelscript.appfwk.apps.pcapmgr.models import PCAPStore, PcapDataFile
from steelscript.appfwk.apps.pcapmgr.forms import PcapFileForm, \
    PcapFileListForm
from steelscript.appfwk.apps.pcapmgr.serializers import PcapDataFileSerializer
from steelscript.common.service import Auth


logger = logging.getLogger(__name__)


class PcapFileDetail(views.APIView):
    """ Display File detail view """

    model = PcapDataFile
    serializer_class = PcapDataFileSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
    permission_classes = (IsAuthenticated,)

    def get(self, request, pcapfile_id=None):
        if request.accepted_renderer.format == 'html':
            if pcapfile_id:
                datafile = get_object_or_404(PcapDataFile, pk=pcapfile_id)
                form = PcapFileForm(instance=datafile)
            else:
                form = PcapFileForm()
            return Response({'form': form, 'auth': Auth},
                            template_name='pcapfile_detail.html')
        else:
            datafile = get_object_or_404(PcapDataFile, pk=pcapfile_id)
            serializer = PcapDataFileSerializer(instance=datafile)
            data = serializer.data
            return Response(data)

    def post(self, request, pcapfile_id=None):
        if pcapfile_id is not None:
            datafile = get_object_or_404(PcapDataFile, pk=pcapfile_id)
            form = PcapFileForm(request.DATA, instance=datafile)
        else:
            form = PcapFileForm(data=request.DATA,
                                files=request.FILES)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('pcapfile-list'))
        else:
            return Response({'form': form, 'auth': Auth},
                            template_name='pcapfile_detail.html')

    def delete(self, request, pcapfile_id):
        datafile = get_object_or_404(PcapDataFile, pk=pcapfile_id)
        PCAPStore.delete(datafile.datafile.name)
        datafile.delete()
        return HttpResponse(status=204)


class PcapFileList(generics.ListAPIView):
    model = PcapDataFile
    serializer_class = PcapDataFileSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
    permission_classes = (IsAuthenticated,)

    supported_files = ', '.join((file['name'] for file in
                                model.SUPPORTED_FILES.values()))

    def get(self, request, *args, **kwargs):
        queryset = PcapDataFile.objects.order_by('id')

        if request.accepted_renderer.format == 'html':
            df_form_set = modelformset_factory(PcapDataFile,
                                               form=PcapFileListForm,
                                               extra=0)
            formset = df_form_set(queryset=queryset)
            tabledata = zip(formset.forms, queryset)
            data = {'formset': formset, 'tabledata': tabledata,
                    'auth': Auth, 'supported_files': self.supported_files}
            return Response(data, template_name='pcapfile_list.html')

        serializer = PcapDataFileSerializer(instance=queryset)
        data = serializer.data
        return Response(data)

    def put(self, request, *args, **kwargs):
        """ Function to save changes to multiple devices once.

        This function is called only when the "Save Changes" button is
        clicked on /devices/ page. However, it only supports enable/disable
        device(s). The url sent out will only include 'enable' field.
        """

        df_form_set = modelformset_factory(PcapDataFile,
                                           form=PcapFileListForm,
                                           extra=0)
        formset = df_form_set(request.DATA)

        if formset.is_valid():
            formset.save()
            if '/pcapmgr' not in request.META['HTTP_REFERER']:
                return HttpResponseRedirect(request.META['HTTP_REFERER'])
            else:
                return HttpResponseRedirect(reverse('pcapfile-list'))

        else:
            data = {'formset': formset, 'auth': Auth,
                    'supported_files': self.supported_files}
            return Response(data, template_name='pcapfile_list.html')
