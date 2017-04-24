# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import logging
import datetime
from os import stat, path
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, HttpResponse, \
    StreamingHttpResponse
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import get_object_or_404

from rest_framework import generics, views
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from steelscript.appfwk.apps.pcapmgr.models import pcap_store, PcapDataFile, \
    PcapFileField, WARN_PCAP
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
                f_name = path.basename(datafile.datafile.url)
            else:
                form = PcapFileForm()
                f_name = None
            return Response({'form': form, 'file_name': f_name},
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
        pcap_store.delete(datafile.datafile.name)
        datafile.delete()
        return HttpResponse(status=204)


class PcapFileList(generics.ListAPIView):
    model = PcapDataFile
    serializer_class = PcapDataFileSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
    permission_classes = (IsAuthenticated,)

    supported_files = ', '.join(model.SUPPORTED_FILES.keys())

    def get(self, request, *args, **kwargs):
        queryset = PcapDataFile.objects.order_by('id')

        if request.accepted_renderer.format == 'html':
            df_form_set = modelformset_factory(PcapDataFile,
                                               form=PcapFileListForm,
                                               extra=0)
            formset = df_form_set(queryset=queryset)
            tabledata = queryset
            data = {'formset': formset, 'tabledata': tabledata,
                    'supported_files': self.supported_files,
                    'pcap_lib_warning': WARN_PCAP}
            return Response(data, template_name='pcapfile_list.html')

        serializer = PcapDataFileSerializer(instance=queryset)
        data = serializer.data
        return Response(data)


class PcapFSSync(views.APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        """
        Runs an operation to sync the file system and the DB.
        redirects to the list view.
        """

        added_files = 0
        removed_db = 0
        ignored_files = 0

        removed_storage_loc = False

        # First check that the directory is present. If not then
        # there can't be any files.
        if path.exists(pcap_store.location):
            fs_files = list()
            _, fs_raw_files = pcap_store.listdir(pcap_store.location)
            for f in fs_raw_files:
                t_name, t_code = PcapFileField.get_magic_type(
                    pcap_store.open(f)
                )
                # Only take files supported by the field and storage.
                # ignore the rest.
                if t_name:
                    fs_files.append(f)
                else:
                    ignored_files += 1
            db_files = PcapDataFile.objects.order_by('id')

            # first pass look in the db and delete any records that
            # don't have a file system object.
            for (fname, datafile) in [(path.basename(dbfile.datafile.name),
                                       dbfile) for dbfile in db_files]:
                if not fs_files.count(fname):
                    datafile.delete()
                    removed_db += 1

            # now look over the file system files to see if are are not
            # in the DB
            db_file_names = [path.basename(dbfile.datafile.name) for dbfile in
                             PcapDataFile.objects.order_by('id')]
            for fsfile in fs_files:
                if not db_file_names.count(fsfile):
                    f = pcap_store.path(fsfile)
                    t_name, t_sig = \
                        PcapFileField.get_magic_type(pcap_store.open(f))
                    new_db = PcapDataFile(description=fsfile,
                                          uploaded_at=(
                                              pcap_store.created_time(fsfile)),
                                          file_type=t_name,
                                          datafile=f,
                                          start_time=datetime.datetime.now(),
                                          end_time=datetime.datetime.now()
                                          )
                    new_db.save()
                    added_files += 1
        else:
            db_files = PcapDataFile.objects.order_by('id')
            if db_files:
                removed_storage_loc = True

        if removed_storage_loc:
            msg = ('Warning: PCAP records found in the database but the '
                   'underlying storage location is missing. This could be '
                   'caused by issues such as file system corruption. Please i'
                   'nvestigate.')
        else:
            msg = ('PCAP Manager Sync: {0} PCAP record(s) removed from '
                   'database. {1} new file object(s) added to database{2}')

            skipped = '.'
            if ignored_files:
                skipped = ' ({0} file(s) with invalid type skipped).'.format(
                    ignored_files
                )
            msg = msg.format(removed_db, added_files, skipped)

        messages.add_message(request._request, messages.INFO, msg)

        return HttpResponseRedirect(reverse('pcapfile-list'))


def pcap_download(request, pcap_name=None):
    if pcap_name is not None:
        file_path = pcap_store.path(pcap_name)
        chunk_size = 16384
        response = StreamingHttpResponse(FileWrapper(open(file_path,
                                                          'rb'),
                                         chunk_size))

        response['Content-Type'] = 'application/vnd.tcpdump.pcap'
        response['Content-Length'] = \
            stat(pcap_store.path(pcap_name)).st_size
        response['Content-Disposition'] = ('attachment; filename={0}'
                                           ''.format(pcap_name))
        return response
    else:
        return HttpResponseRedirect(reverse('pcapfile-list'))
