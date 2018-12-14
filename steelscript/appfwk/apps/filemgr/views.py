# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import logging
import magic
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

from steelscript.appfwk.apps.filemgr.filestore import file_store
from steelscript.appfwk.apps.filemgr.models import DataFile
from steelscript.appfwk.apps.filemgr.forms import DataFileForm
from steelscript.appfwk.apps.filemgr.serializers import DataFileSerializer

logger = logging.getLogger(__name__)
mime_type = magic.Magic(mime=True)
type_desc = magic.Magic()

class DataFileDetail(views.APIView):

    model = DataFile
    serializer_class = DataFileSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
    permission_classes = (IsAuthenticated,)

    def get(self, request, datafile_id=None):
        if request.accepted_renderer.format == 'html':
            if datafile_id:
                datafile = get_object_or_404(DataFile, pk=datafile_id)
                form = DataFileForm(instance=datafile)
                f_name = path.basename(datafile.datafile.url)
            else:
                form = DataFileForm()
                f_name = None
            return Response({'form': form, 'file_name': f_name},
                            template_name='datafile_detail.html')
        else:
            datafile = get_object_or_404(DataFile, pk=datafile_id)
            serializer = DataFileSerializer(instance=datafile)
            data = serializer.data
            return Response(data)

    def post(self, request, datafile_id=None):
        if datafile_id is not None:
            datafile = get_object_or_404(DataFile, pk=datafile_id)
            form = DataFileForm(request.DATA, instance=datafile)
        else:
            form = DataFileForm(data=request.DATA,
                                files=request.FILES)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('datafile-list'))
        else:
            return Response({'form': form},
                            template_name='datafile_detail.html')

    def delete(self, request, datafile_id):
        datafile = get_object_or_404(DataFile, pk=datafile_id)
        file_store.delete(datafile.datafile.name)
        datafile.delete()
        return HttpResponse(status=204)


class DataFileList(generics.ListAPIView):
    model = DataFile
    serializer_class = DataFileSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        queryset = DataFile.objects.order_by('id')

        if request.accepted_renderer.format == 'html':
            df_form_set = modelformset_factory(DataFile,
                                               form=DataFileForm,
                                               extra=0)
            formset = df_form_set(queryset=queryset)
            tabledata = queryset
            data = {'formset': formset, 'tabledata': tabledata}
            return Response(data, template_name='datafile_list.html')

        serializer = DataFileSerializer(instance=queryset)
        data = serializer.data
        return Response(data)


class DataFSSync(views.APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):

        added_files = 0
        removed_db = 0

        removed_storage_loc = False

        if path.exists(file_store.location):
            fs_files = list()
            _, fs_raw_files = file_store.listdir(file_store.location)
            for f in fs_raw_files:
                fs_files.append(f)
            db_files = DataFile.objects.order_by('id')

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
                             DataFile.objects.order_by('id')]
            for fsfile in fs_files:
                if not db_file_names.count(fsfile):
                    f = file_store.path(fsfile)
                    new_db = DataFile(description=fsfile,
                                      uploaded_at=(
                                          file_store.created_time(fsfile)
                                      ),
                                      file_type=type_desc.from_file(f),
                                      file_bytes=stat(f).st_size,
                                      datafile=f)
                    new_db.save()
                    added_files += 1
        else:
            db_files = DataFile.objects.order_by('id')
            if db_files:
                removed_storage_loc = True

        if removed_storage_loc:
            msg = ('Warning: Data file records found in the database but the '
                   'underlying storage location is missing. This could be '
                   'caused by issues such as file system corruption. Please i'
                   'nvestigate.')
        else:
            msg = ('Data File Manager Sync: {0} Data File record(s) removed '
                   'from database. {1} new file object(s) added to '
                   'database{2}')

            skipped = '.'
            msg = msg.format(removed_db, added_files, skipped)

        messages.add_message(request._request, messages.INFO, msg)

        return HttpResponseRedirect(reverse('datafile-list'))


def file_download(request, file_name=None):
    if file_name is not None:
        file_path = file_store.path(file_name)
        chunk_size = 16384

        response = StreamingHttpResponse(FileWrapper(open(file_path,
                                                          'rb'),
                                         chunk_size))

        response['Content-Type'] = mime_type.from_file(file_path)
        response['Content-Length'] = stat(file_path).st_size
        response['Content-Disposition'] = ('attachment; filename={0}'
                                           ''.format(file_name))
        return response
    else:
        return HttpResponseRedirect(reverse('datafile-list'))
