# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import logging
import datetime
from django.contrib import messages
from os.path import basename
from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import generics, views
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from steelscript.appfwk.apps.pcapmgr.models import PCAPStore, PcapDataFile, \
    PcapFileField
from steelscript.appfwk.apps.pcapmgr.forms import PcapFileForm, \
    PcapFileListForm
from steelscript.appfwk.apps.pcapmgr.serializers import PcapDataFileSerializer

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
            return Response({'form': form},
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
            return Response({'form': form},
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
                    'supported_files': self.supported_files,
                    'pcap_lib_warning': self.model.pcap_warning}
            return Response(data, template_name='pcapfile_list.html')

        serializer = PcapDataFileSerializer(instance=queryset)
        data = serializer.data
        return Response(data)

    def put(self, request, *args, **kwargs):

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
            data = {'formset': formset,
                    'supported_files': self.supported_files,
                    'no_pcap_warning': self.model.pcap_warning}
            return Response(data, template_name='pcapfile_list.html')


class PcapFSSync(views.APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        """
        Runs an ASYNC operation to sync the file system and the DB.
        redirects to the list view.
        """

        added_files = list()
        removed_db = list()
        ignored_files = list()

        fs_files = list()
        fs_raw_files = PCAPStore.listdir(PCAPStore.location)[1]
        for f in fs_raw_files:
            ftype = PcapFileField.get_magic_type(PCAPStore.open(f))
            # Only take files supported by the field and storage.
            # ignore the rest.
            if ftype[0]:
                fs_files.append(f)
            else:
                ignored_files.append(f)
        db_files = PcapDataFile.objects.order_by('id')

        # first pass look in the db and delete any records that
        # don't have a file system object.
        for (fname, datafile) in [(basename(dbfile.datafile.name),
                                   dbfile) for dbfile in db_files]:
            if not fs_files.count(fname):
                datafile.delete()
                removed_db.append(fname)

        # now look over the file system files to see if are are not
        # in the DB
        db_file_names = [basename(dbfile.datafile.name) for dbfile in
                         PcapDataFile.objects.order_by('id')]
        for fsfile in fs_files:
            if not db_file_names.count(fsfile):
                f = PCAPStore.path(fsfile)
                ftype = PcapFileField.get_magic_type(PCAPStore.open(f))
                new_db = PcapDataFile(description=fsfile,
                                      uploaded_at=(
                                          PCAPStore.created_time(fsfile)),
                                      file_type=ftype[0],
                                      datafile=f,
                                      start_time=datetime.datetime.now(),
                                      end_time=datetime.datetime.now()
                                      )
                new_db.save()
                added_files.append(fsfile)

        msg = ('PCAP Manager Sync: {0} PCAP record(s) removed from database.'
               ' {1} new file object(s) added to database{2}')

        skipped = '.'
        if len(ignored_files):
            skipped = ' ({0} file(s) with invalid type skipped).'.format(
                len(ignored_files)
            )

        messages.add_message(request._request, messages.INFO,
                             msg.format(len(removed_db),
                                        len(added_files),
                                        skipped))
        return HttpResponseRedirect(reverse('pcapfile-list'))