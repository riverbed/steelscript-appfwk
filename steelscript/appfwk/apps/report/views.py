# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import re
import os
import sys
import cgi
import math
import time
import json
import uuid
import shutil
import datetime
import importlib
import traceback
import logging
from collections import OrderedDict

import pytz
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.http import JsonResponse
from django.template import loader, RequestContext
from django.template.defaultfilters import date
from django.shortcuts import render_to_response, get_object_or_404
from django.core import management
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError

from rest_framework import generics, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.authentication import (SessionAuthentication,
                                           BasicAuthentication)
from steelscript.appfwk.apps.jobs.models import Job

from steelscript.common.timeutils import round_time, timedelta_total_seconds, \
    parse_timedelta, sec_string_to_datetime, datetime_to_seconds
from steelscript.commands.steel import shell, ShellFailed
from steelscript.appfwk.apps.datasource.serializers import TableSerializer
from steelscript.appfwk.apps.datasource.forms import TableFieldForm
from steelscript.appfwk.apps.devices.models import Device
from steelscript.appfwk.apps.geolocation.models import Location, LocationIP
from steelscript.appfwk.apps.preferences.models import (SystemSettings,
                                                        AppfwkUser)
from steelscript.appfwk.apps.report.models import (Report, Section, Widget,
                                                   WidgetJob, WidgetAuthToken,
                                                   WidgetDataCache,
                                                   ReportHistory, ReportStatus)
from steelscript.appfwk.apps.report.serializers import ReportSerializer, \
    WidgetSerializer
from steelscript.appfwk.apps.report.utils import create_debug_zipfile
from steelscript.appfwk.apps.report.forms import (ReportEditorForm,
                                                  CopyReportForm)
from steelscript.appfwk.project.middleware import URLTokenAuthentication


logger = logging.getLogger(__name__)


@api_view(('GET',))
@permission_classes((IsAdminUser,))
def reload_config(request, namespace=None, report_slug=None):
    """ Reload all reports or one specific report
    """
    if namespace and report_slug:
        logger.debug("Reloading %s report" % report_slug)
        management.call_command('reload',
                                namespace=namespace,
                                report_name=report_slug)
    elif namespace:
        logger.debug("Reloading reports under namespace %s" % namespace)
        management.call_command('reload', namespace=namespace)
    else:
        logger.debug("Reloading all reports")
        management.call_command('reload')

    # prioritize next param over HTTP_REFERERs
    if hasattr(request, 'QUERY_PARAMS') and 'next' in request.QUERY_PARAMS:
        return HttpResponseRedirect(request.QUERY_PARAMS['next'])
    elif ('HTTP_REFERER' in request.META and
          'reload' not in request.META['HTTP_REFERER']):
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        return HttpResponseRedirect(reverse('report-view-root'))


def download_debug(request):
    """ Create zipfile and send it back to client
    """
    # XXX when we implement RBAC this method needs to be ADMIN-level only

    zipfile = create_debug_zipfile()
    wrapper = FileWrapper(file(zipfile))
    response = HttpResponse(wrapper, content_type='application/zip')
    zipname = os.path.basename(zipfile)
    response['Content-Disposition'] = 'attachment; filename=%s' % zipname
    response['Content-Length'] = os.stat(zipfile).st_size
    return response


def rm_file(filepath):
    """ Remove a file, ignoring errors that may occur

    :param filepath: file name with path
    """
    try:
        os.remove(filepath)
    except:
        pass


def get_timezone(request):
        if request.user.is_authenticated():
            return pytz.timezone(request.user.timezone)
        else:
            return pytz.timezone(settings.GUEST_USER_TIME_ZONE)


class GenericReportView(views.APIView):

    def get_media_params(self, request):
        """ Implement this method in subclasses to compute the values of
            the template, criteria and expand_tables template params.
        """

        raise NotImplementedError('get_media_params() must be implemented in '
                                  ' subclass.')

    def report_def(self, widgets, report_time, debug=False):
        """Return dict for report definition."""
        meta = {
            'datetime': str(date(report_time, 'jS F Y H:i:s')),
            'timezone': str(report_time.tzinfo),
            'debug': debug
        }
        return {'meta': meta, 'widgets': widgets}

    def is_field_cls(self, field, cls_name):
        """Determine if a field is of a certain field class."""
        return (field.field_cls and
                field.field_cls.__name__ == cls_name)

    def update_criteria_from_bookmark(self, report, request, fields):
        """ Update fields' initial values using bookmark. """
        request_data = request.GET.dict()
        override_msg = 'Setting criteria field %s to %s.'

        # Initialize report.live as False
        report.live = False

        for k, v in request_data.iteritems():
            if k == 'auto_run':
                report.auto_run = (v.lower() == 'true')
                continue

            if k == 'live':
                if report.static and v.lower() == 'true':
                    report.live = True
                continue

            field = fields.get(k, None)
            if field is None:
                logger.warning("Keyword %s in bookmark does not match any "
                               "criteria field." % k)
                continue

            if self.is_field_cls(field, 'DateTimeField'):
                # Only accepts epoch seconds
                if not v.isdigit():
                    field.error_msg = ("%s '%s' is invalid." % (k, v))
                    continue

                # Needs to set delta derived from ceiling of current time
                # Otherwise the resulting timestamp would advance 1 sec
                # vs the original timestamp from bookmark
                delta = int(math.ceil(time.time())) - int(v)
                if delta < 0:
                    field.error_msg = ("%s %s is later than current time."
                                       % (k, v))
                    continue

                dt_utc = sec_string_to_datetime(int(v))
                tz = get_timezone(request)
                dt_local = dt_utc.astimezone(tz)

                logger.debug(override_msg % (k, dt_local))
                # Setting initial date as 'mm/dd/yy'
                field.field_kwargs['widget_attrs']['initial_date'] = \
                    dt_local.strftime('%m/%d/%Y')
                # Setting initial time as 'hh:mm:ss'
                field.field_kwargs['widget_attrs']['initial_time'] = \
                    dt_local.strftime('%H:%M:%S')

            elif self.is_field_cls(field, 'BooleanField'):
                logger.debug(override_msg % (k, v.lower() == 'true'))
                field.initial = (v.lower() == 'true')

            else:
                logger.debug(override_msg % (k, v))
                field.initial = v

    def render_html(self, report, request, namespace, report_slug, isprint):
        """ Render HTML response
        """
        logger.debug('Received request for report page: %s' % report_slug)

        if request.user.is_authenticated() and not request.user.profile_seen:
            # only redirect if first login
            return HttpResponseRedirect(reverse('preferences')+'?next=/report')

        devices = Device.objects.filter(enabled=True)
        device_modules = [obj.module for obj in devices]

        # iterate through all sections of the report, for each section,
        # iterate through the fields, and if any field's
        # pre_process_func function is device_selection_preprocess
        # then the field is a device field, then fetch the module and check
        # the module is included in Device objects in database
        missing_devices = set()
        for _id, fields in report.collect_fields_by_section().iteritems():
            for _name, field_obj in fields.iteritems():
                func = field_obj.pre_process_func
                if (func and func.function == 'device_selection_preprocess'):
                    # This field is a device field,
                    # check if the device is configured
                    module = func.params['module']
                    if module not in device_modules:
                        missing_devices.add(module)
        if missing_devices:
            missing_devices = ', '.join(list(missing_devices))

        if request.user.is_authenticated() and not request.user.profile_seen:
            # only redirect if first login
            return HttpResponseRedirect(reverse('preferences')+'?next=/report')

        # Setup default criteria for the report based on underlying tables
        system_settings = SystemSettings.get_system_settings()
        form_init = {'ignore_cache': system_settings.ignore_cache}
        for table in report.tables():
            if table.criteria:
                form_init.update(table.criteria)

        # Collect all fields organized by section, with section id 0
        # representing common report level fields
        fields_by_section = report.collect_fields_by_section()

        # Merge fields into a single dict for use by the Django Form # logic
        all_fields = OrderedDict()
        [all_fields.update(c) for c in fields_by_section.values()]

        self.update_criteria_from_bookmark(report, request, all_fields)

        form = TableFieldForm(all_fields,
                              hidden_fields=report.hidden_fields,
                              initial=form_init)

        # Build a section map that indicates which section each field
        # belongs in when displayed
        section_map = []
        if fields_by_section[0]:
            section_map.append({'title': 'Common',
                                'parameters': fields_by_section[0]})

        for s in Section.objects.filter(report=report).order_by('position',
                                                                'title'):
            show = False
            for v in fields_by_section[s.id].values():
                if v.keyword not in (report.hidden_fields or []):
                    show = True
                    break

            if show:
                section_map.append({'title': s.title,
                                    'parameters': fields_by_section[s.id]})

        template, criteria, expand_tables = self.get_media_params(request)

        return render_to_response(
            template,
            {'report': report,
             'developer': system_settings.developer,
             'maps_version': system_settings.maps_version,
             'maps_api_key': system_settings.maps_api_key,
             'weather_enabled': system_settings.weather_enabled,
             'weather_url': system_settings.weather_url,
             'endtime': 'endtime' in form.fields,
             'form': form,
             'section_map': section_map,
             'show_sections': (len(section_map) > 1),
             'criteria': criteria,
             'expand_tables': expand_tables,
             'missing_devices': missing_devices,
             'is_superuser': request.user.is_superuser},
            context_instance=RequestContext(request)
        )


class ReportView(GenericReportView):
    """ Main handler for /report/{id}
    """
    model = Report
    serializer_class = ReportSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    def get_media_params(self, request):
        template = 'report.html'
        criteria = 'null'
        expand_tables = False

        return template, criteria, expand_tables

    # ReportView.get()
    def get(self, request, namespace=None, report_slug=None):
        if request.accepted_renderer.format == 'html':  # handle HTML calls
            queryset = Report.objects.filter(enabled=True).order_by('position',
                                                                    'title')

            try:
                if namespace is None:
                    namespace = queryset[0].namespace

                if report_slug is None:
                    qs = queryset.filter(namespace=namespace)
                    kwargs = {'report_slug': qs[0].slug,
                              'namespace': namespace}
                    return HttpResponseRedirect(reverse('report-view',
                                                        kwargs=kwargs))
                else:
                    report = queryset.get(namespace=namespace,
                                          slug=report_slug)
            except:
                raise Http404

            return self.render_html(report, request, namespace, report_slug,
                                    False)
        else:  # handle REST calls
            queryset = Report.objects.filter(enabled=True)
            if namespace and report_slug:
                queryset = queryset.get(namespace=namespace,
                                        slug=report_slug)
            elif report_slug:
                queryset = queryset.get(namespace='default',
                                        slug=report_slug)
            elif namespace:
                queryset = queryset.filter(namespace='default')

            serializer = ReportSerializer(instance=queryset)
            return Response(serializer.data)

    # ReportView.post()
    def post(self, request, namespace=None, report_slug=None):
        if namespace is None or report_slug is None:
            return self.http_method_not_allowed(request)

        logger.debug("Received POST for report %s, with params: %s" %
                     (report_slug, request.POST))

        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)

        fields_by_section = report.collect_fields_by_section()
        all_fields = OrderedDict()
        [all_fields.update(c) for c in fields_by_section.values()]
        form = TableFieldForm(all_fields, hidden_fields=report.hidden_fields,
                              data=request.POST, files=request.FILES)

        if form.is_valid():
            logger.debug('Form passed validation: %s' % form)
            formdata = form.cleaned_data
            logger.debug('Form cleaned data: %s' % formdata)

            # parse time and localize to user profile timezone
            timezone = get_timezone(request)
            form.apply_timezone(timezone)

            if formdata['debug']:
                logger.debug("Debugging report and rotating logs now ...")
                management.call_command('rotate_logs')

            logger.debug("Report %s validated form: %s" %
                         (report_slug, formdata))

            # construct report definition
            now = datetime.datetime.now(timezone)
            widgets = report.widget_definitions(form.as_text())

            report_def = self.report_def(widgets, now, formdata['debug'])

            logger.debug("Sending widget definitions for report %s: %s" %
                         (report_slug, report_def))

            if settings.REPORT_HISTORY_ENABLED:
                create_report_history(request, report, widgets)

            return JsonResponse(report_def, safe=False)
        else:
            # return form with errors attached in a HTTP 400 Error response
            return HttpResponse(str(form.errors), status=400)


class ReportAutoView(GenericReportView):
    """Return default criteria values, with latest time, if applicable.

    Used in auto-run reports when specifying detailed criteria isn't
    necessary.

    Also used by individual widgets for retrieving updated criteria values.
    """
    authentication_classes = (SessionAuthentication,
                              BasicAuthentication,
                              URLTokenAuthentication)

    def get_media_params(self, request):
        # json only - no media needed
        pass

    def get(self, request, namespace=None, report_slug=None, widget_slug=None):
        try:
            report = Report.objects.get(namespace=namespace,
                                        slug=report_slug)
        except:
            raise Http404

        logger.debug("Received GET for report %s widget definition" %
                     report_slug)

        if widget_slug:
            w = get_object_or_404(
                Widget,
                slug=widget_slug,
                section__in=Section.objects.filter(report=report)
            )
            widgets = [w]
        else:
            # Add 'id' to order_by so that stacked widgets will return
            # with the same order as created
            widgets = report.widgets().order_by('row', 'col', 'id')

        # parse time and localize to user profile timezone
        timezone = get_timezone(request)
        now = datetime.datetime.now(timezone)

        # pin the endtime to a round interval if we are set to
        # reload periodically
        minutes = report.reload_minutes
        offset = report.reload_offset
        if minutes:
            # avoid case of long duration reloads to have large reload gap
            # e.g. 24-hour report will consider 12:15 am or later a valid time
            # to roll-over the time time values, rather than waiting
            # until 12:00 pm
            trimmed = round_time(dt=now, round_to=60*minutes, trim=True)
            if now - trimmed > datetime.timedelta(seconds=offset):
                now = trimmed
            else:
                now = round_time(dt=now, round_to=60*minutes)

        widget_defs = []

        for w in widgets:
            # get default criteria values for widget
            # and set endtime to now, if applicable
            widget_fields = w.collect_fields()
            form = TableFieldForm(widget_fields, use_widgets=False)

            # create object from the tablefield keywords
            # and populate it with initial data generated by default
            keys = form._tablefields.keys()
            criteria = dict(zip(keys, [None]*len(keys)))
            criteria.update(form.data)

            # calculate time offsets
            if 'endtime' in criteria:
                criteria['endtime'] = now.isoformat()

                # only consider starttime if its paired with an endtime
                if 'starttime' in criteria:
                    start = now
                    field = form.fields['starttime']
                    initial = field.widget.attrs.get('initial_time', None)
                    if initial:
                        m = re.match("now *- *(.+)", initial)
                        if m:
                            delta = parse_timedelta(m.group(1))
                            start = now - delta

                    criteria['starttime'] = start.isoformat()

            # Check for "Meta Widget" criteria items
            system_settings = SystemSettings.get_system_settings()
            if system_settings.ignore_cache:
                criteria['ignore_cache'] = system_settings.ignore_cache
            if system_settings.developer:
                criteria['debug'] = system_settings.developer

            # setup json definition object
            widget_def = w.get_definition(criteria)
            widget_defs.append(widget_def)

            # Build the primary key corresponding to static data for this
            # widget
            if report.static:
                rw_id = '-'.join([namespace, report_slug,
                                  widget_def['widgetslug']])
                # Add cached widget data if available.
                try:
                    data_cache = WidgetDataCache.objects.get(
                        report_widget_id=rw_id)
                    widget_def['dataCache'] = data_cache.data
                except WidgetDataCache.DoesNotExist:
                    msg = "No widget data cache available with id %s." % rw_id
                    resp = {'message': msg,
                            'status': 'error',
                            'exception': ''}
                    widget_def['dataCache'] = json.dumps(resp)
        report_def = self.report_def(widget_defs, now)

        return JsonResponse(report_def, safe=False)


class ReportPrintView(GenericReportView):
    """ Handles printer-friendly report pages
    """
    model = Report
    serializer_class = ReportSerializer
    renderer_classes = (TemplateHTMLRenderer, )

    def get_media_params(self, request):
        template = 'report_print.html'
        criteria = json.dumps(dict(zip(request.POST.keys(),
                                       request.POST.values())))
        expand_tables = ('expand_tables' in request.POST and
                         request.POST['expand_tables'] != '')
        return template, criteria, expand_tables

    def post(self, request, namespace, report_slug):
        queryset = Report.objects.filter(enabled=True)
        try:
            report = queryset.get(namespace=namespace, slug=report_slug)
        except:
            raise Http404

        return self.render_html(report, request, namespace, report_slug, True)


def create_report_history(request, report, widgets):
    """Create a report history object.

    :param request: request object
    :param report: Report object
    :param widgets: List of widget definitions
    """

    # create the form to derive criteria for bookmark only
    # the form in the calling context can not be used
    # because it does not include hidden fields
    fields_by_section = report.collect_fields_by_section()
    all_fields = OrderedDict()
    [all_fields.update(c) for c in fields_by_section.values()]

    form = TableFieldForm(all_fields,
                          hidden_fields=report.hidden_fields,
                          include_hidden=True,
                          data=request.POST,
                          files=request.FILES)

    # parse time and localize to user profile timezone
    timezone = get_timezone(request)
    form.apply_timezone(timezone)

    form_data = form.cleaned_data

    url = request._request.path + '?'

    # form_data contains fields that don't belong to url
    # e.g. ignore_cache, debug
    # thus use compute_field_precedence method to filter those
    table_fields = {k: form_data[k] for k in form.compute_field_precedence()}

    # Convert field values into strings suitable for bookmark
    def _get_url_fields(flds):
        for k, v in flds.iteritems():
            if k in ['starttime', 'endtime']:
                yield (k, str(datetime_to_seconds(v)))
            elif k in ['duration', 'resolution']:
                try:
                    yield (k, str(int(timedelta_total_seconds(v))))
                except AttributeError:
                    # v is of special value, not a string of some duration
                    yield (k, v.replace(' ', '+'))
            else:
                # use + as encoded white space
                yield (k, str(v).replace(' ', '+'))
        yield ('auto_run', 'true')

    url_fields = ['='.join([k, v]) for k, v in _get_url_fields(table_fields)]

    # Form the bookmark link
    url += '&'.join(url_fields)

    last_run = datetime.datetime.now(timezone)

    # iterate over the passed in widget definitions and use those
    # to calculate the actual job handles
    # since these will mimic what gets used to create the actual jobs,
    # the criteria will match more closely than using the report-level
    # criteria data
    handles = []
    for widget in widgets:
        wobj = Widget.objects.get(
            slug=widget['widgetslug'],
            section__in=Section.objects.filter(report=report)
        )

        fields = wobj.collect_fields()
        form = TableFieldForm(fields, use_widgets=False,
                              hidden_fields=report.hidden_fields,
                              include_hidden=True,
                              data=widget['criteria'], files=request.FILES)

        if form.is_valid():
            # parse time and localize to user profile timezone
            timezone = get_timezone(request)
            form.apply_timezone(timezone)

            form_criteria = form.criteria()
            widget_table = wobj.table()
            form_criteria = form_criteria.build_for_table(widget_table)
            try:
                form_criteria.compute_times()
            except ValueError:
                pass

            handle = Job._compute_handle(widget_table, form_criteria)
            logger.debug('ReportHistory: adding handle %s for widget_table %s'
                         % (handle, widget_table))
            handles.append(handle)

        else:
            # log error, but don't worry about it for adding to RH
            logger.warning("Error while calculating job handle for Widget %s, "
                           "internal criteria form is invalid: %s" %
                           (wobj, form.errors.as_text()))

    job_handles = ','.join(handles)

    if request.user.is_authenticated():
        user = request.user.username
    else:
        user = settings.GUEST_USER_NAME

    logger.debug('Creating ReportHistory for user %s at URL %s' % (user, url))

    ReportHistory.create(namespace=report.namespace,
                         slug=report.slug,
                         bookmark=url,
                         first_run=last_run,
                         last_run=last_run,
                         job_handles=job_handles,
                         user=user,
                         criteria=table_fields,
                         run_count=1)


class ReportHistoryView(views.APIView):
    """ Display a list of report history. """

    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAuthenticated, )   # no guests

    def get(self, request):
        return Response({'history': ReportHistory.objects.order_by('-last_run'),
                         'status': ReportStatus},
                        template_name='history.html')


class ReportEditor(views.APIView):
    """ Edit Report files directly.  Requires superuser permissions. """
    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAdminUser, )

    def _git_repo(self):
        # check if git enabled for this project
        try:
            shell(cmd='git status', cwd=settings.PROJECT_ROOT, allow_fail=True)
            return True
        except ShellFailed:
            return False

    def get(self, request, namespace, report_slug):
        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)
        form = ReportEditorForm(report.filepath)
        copyform = CopyReportForm(report)
        return render_to_response('edit.html',
                                  {'report': report,
                                   'form': form,
                                   'ajaxform': copyform,
                                   'gitavail': self._git_repo()},
                                  context_instance=RequestContext(request))

    def post(self, request, namespace, report_slug):
        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)
        form = ReportEditorForm(report.filepath, request.POST)
        if form.is_valid():
            form.save()
            msg = 'Report %s saved.' % report.filepath
        else:
            msg = 'Problem saving report ... review content.'

        messages.add_message(request._request, messages.INFO, msg)
        copyform = CopyReportForm(report)
        return render_to_response('edit.html',
                                  {'report': report,
                                   'form': form,
                                   'ajaxform': copyform,
                                   'gitavail': self._git_repo()},
                                  context_instance=RequestContext(request))


class ReportEditorDiff(views.APIView):
    """ Show git diff of report file.  Requires superuser permissions. """
    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAdminUser, )

    def get(self, request, namespace, report_slug):
        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)
        from ansi2html import Ansi2HTMLConverter
        conv = Ansi2HTMLConverter(inline=True, dark_bg=False)
        ansi = shell('git diff --color %s' % report.filepath, save_output=True)
        html = conv.convert(ansi, full=False)
        if (not html and shell('git ls-files %s' % report.filepath,
                               save_output=True)):
            html = 'No changes.'
        else:
            html = 'File not committed to git repository.'

        return render_to_response('editdiff.html',
                                  {'report': report,
                                   'diffhtml': html},
                                  context_instance=RequestContext(request))


class ReportCopy(views.APIView):
    """ Edit Report files directly.  Requires superuser permissions. """
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
    permission_classes = (IsAdminUser, )

    def get(self, request, namespace, report_slug):
        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)
        form = CopyReportForm(report)
        return render_to_response('ajax_form.html',
                                  {'form': form},
                                  context_instance=RequestContext(request))

    def update_title(self, report, form):
        """ Writes new title into file"""
        with open(form.filepath(), "r+") as f:
            lines = f.read().split("\n")
            new_line = None
            for ind, ln in enumerate(lines):
                if "Report.create" in ln and not ln.startswith('#'):
                    new_line = ln.replace(report.title, form.reportname)
                    break
            if new_line is None:
                raise ValidationError("Current report does not have title")
            lines[ind] = new_line
            f.seek(0)
            f.write("\n".join(lines))
            f.truncate()

    def post(self, request, namespace, report_slug):
        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)
        form = CopyReportForm(report, request.POST)
        response = {}
        if form.is_valid():
            try:
                shutil.copyfile(report.filepath, form.filepath())
                # update the title of the new report
                self.update_title(report, form)

                response['redirect'] = reverse('report-editor',
                                               args=(form.namespace,
                                                     form.slug))

                return Response(json.dumps(response))
            except IOError:
                rm_file(form.filepath())
                msg = ('Error copying file from %s to %s' % (report.filepath,
                                                             form.filepath()))
                template = """<li id="message_ajax"><a href="#" onclick="$('#message_ajax').fadeOut(); return false;"><small>clear</small></a> %s</li>'"""
                response['messages'] = template % msg
                return Response(json.dumps(response))
            except Exception, e:
                rm_file(form.filepath())
                msg = ('Error copying report file %s: %s' % (report.filepath,
                                                             str(e)))
                template = """<li id="message_ajax"><a href="#" onclick="$('#message_ajax').fadeOut(); return false;"><small>clear</small></a> %s</li>'"""
                response['messages'] = template % msg
                return Response(json.dumps(response))

        t = loader.get_template('ajax_form.html')
        c = RequestContext(request, {'ajaxform': form})
        response['form'] = t.render(c)
        return Response(json.dumps(response))


class FormCriteria(views.APIView):
    """Process updated criteria form values in report page.

        `post` takes a criteria form and returns a json object of just
               the changed, or dynamic values
    """
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    def post(self, request, namespace=None, report_slug=None):
        # handle REST calls
        if report_slug is None:
            return self.http_method_not_allowed(request)

        logger.debug("Received POST for report %s, with params: %s" %
                     (report_slug, request.POST))

        report = get_object_or_404(Report,
                                   namespace=namespace,
                                   slug=report_slug)

        fields_by_section = report.collect_fields_by_section()
        all_fields = OrderedDict()
        [all_fields.update(c) for c in fields_by_section.values()]

        form = TableFieldForm(all_fields, hidden_fields=report.hidden_fields,
                              data=request.POST, files=request.FILES)

        response = []

        for field in form.dynamic_fields():
            response.append({'id': field.auto_id,
                             'html': str(field)})
        return JsonResponse(response, safe=False)


class ReportTableList(generics.ListAPIView):
    """Return list of tables associated with a given Report."""
    serializer_class = TableSerializer

    def get_queryset(self):
        report = Report.objects.get(namespace=self.kwargs['namespace'],
                                    slug=self.kwargs['report_slug'])
        return report.tables()


class WidgetDetailView(generics.RetrieveAPIView):
    """ Return Widget details looked up by slug field. """
    model = Widget
    lookup_field = 'slug'
    lookup_url_kwarg = 'widget_slug'
    serializer_class = WidgetSerializer
    renderer_classes = (JSONRenderer, )


class WidgetEmbeddedView(views.APIView):
    """ Handler to display embedded widget using default criteria """
    serializer_class = ReportSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    authentication_classes = (URLTokenAuthentication,)

    def get(self, request, namespace=None, report_slug=None, widget_slug=None):
        request_data = request.GET.dict()
        token = request_data['auth']
        del request_data['auth']

        token_obj = WidgetAuthToken.objects.get(token=token)
        criteria_dict = token_obj.criteria

        # request_data carries fields to override the criteria of the widget,
        # each token maps to a list fields that are allowed to be modified,
        # check to ensure each field in request_data:
        # 1. is a valid field included in criteria
        # 2. is included in the editable fields mapping the token in the url
        for field in request_data:
            if field not in criteria_dict:
                msg = "Field '%s' is invalid" % field
                logger.error(msg)
                return HttpResponse(msg, status=403)
            if not token_obj.edit_fields or field not in token_obj.edit_fields:
                msg = "Field '%s' is not allowed to change" % field
                logger.error(msg)
                return HttpResponse(msg, status=403)
            criteria_dict[field] = request_data[field]
        criteria_str = json.dumps(criteria_dict)

        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)

        # widget slugs aren't unique globally, but should be unique within
        # any given report
        w = get_object_or_404(
            Widget,
            slug=widget_slug,
            section__in=Section.objects.filter(report=report)
        )

        system_settings = SystemSettings.get_system_settings()
        widget_def = w.get_definition(mark_safe(criteria_str))

        return render_to_response(
            'widget.html',
            {"widget": widget_def,
             "widget_url": reverse('report-auto-view', args=(namespace,
                                                             report_slug)),
             "widget_authtoken": token,
             'maps_version': system_settings.maps_version,
             'maps_api_key': system_settings.maps_api_key},
            context_instance=RequestContext(request)
        )


class WidgetTokenView(views.APIView):
    parser_classes = (JSONParser,)

    def post(self, request, namespace=None,
             report_slug=None, widget_slug=None):
        logger.debug("Received POST for widget token, widget %s: %s" %
                     (widget_slug, request.POST))

        user = AppfwkUser.objects.get(username=request.user)

        # First remove last '/' at the end
        # then remove authtoken at the end
        pre_url = request.path.rstrip('/').rsplit('/', 1)[0]

        criteria = json.loads(request.POST.dict()['criteria'])

        token = uuid.uuid4().hex
        widget_auth = WidgetAuthToken(token=token,
                                      user=user,
                                      pre_url=pre_url,
                                      criteria=criteria)
        widget_auth.save()

        # Construct label map to facilitate overridden fields display
        report = Report.objects.get(slug=report_slug)
        label_map = {}
        all_fields = {}
        fields_by_section = report.collect_fields_by_section()
        [all_fields.update(fields) for fields in fields_by_section.values()]

        for k in all_fields:
            label_map[k] = all_fields[k].label

        return Response({'auth': token, 'label_map': label_map})


class EditFieldsView(views.APIView):
    parser_classes = (JSONParser,)

    def post(self, request, namespace=None,
             report_slug=None, widget_slug=None, auth_token=None):

        logger.debug("Received POST for adding editable fields, widget %s, "
                     "auth_token %s, request data %s" %
                     (widget_slug, auth_token, request.POST))
        request_data = json.loads(request.POST.dict()['edit_fields'])
        token_obj = WidgetAuthToken.objects.filter(token=auth_token)[0]
        token_obj.edit_fields = request_data
        token_obj.save()
        return Response({})


class WidgetJobsList(views.APIView):
    parser_classes = (JSONParser,)

    authentication_classes = (SessionAuthentication,
                              BasicAuthentication,
                              URLTokenAuthentication)

    def post(self, request, namespace, report_slug, widget_slug, format=None):
        logger.debug("Received POST for report %s, widget %s: %s" %
                     (report_slug, widget_slug, request.POST))

        report = get_object_or_404(Report, namespace=namespace,
                                   slug=report_slug)

        widget = get_object_or_404(
            Widget,
            slug=widget_slug,
            section__in=Section.objects.filter(report=report)
        )

        req_json = json.loads(request.POST['criteria'])

        fields = widget.collect_fields()
        form = TableFieldForm(fields, use_widgets=False,
                              hidden_fields=report.hidden_fields,
                              include_hidden=True,
                              data=req_json, files=request.FILES)

        if not form.is_valid():
            raise ValueError("Widget internal criteria form is invalid:\n%s" %
                             (form.errors.as_text()))

        if form.is_valid():
            logger.debug('Form passed validation: %s' % form)
            formdata = form.cleaned_data
            logger.debug('Form cleaned data: %s' % formdata)

            # parse time and localize to user profile timezone
            timezone = get_timezone(request)
            form.apply_timezone(timezone)

            try:
                form_criteria = form.criteria()
                logger.debug('Form_criteria: %s' % form_criteria)
                job = Job.create(table=widget.table(),
                                 criteria=form_criteria)
                job.start()

                wjob = WidgetJob(widget=widget, job=job)
                wjob.save()

                logger.debug("Created WidgetJob %s for report %s (handle %s)" %
                             (str(wjob), report_slug, job.handle))

                return Response({"joburl": reverse('report-job-detail',
                                                   args=[namespace,
                                                         report_slug,
                                                         widget_slug,
                                                         wjob.id])})
            except Exception as e:
                logger.exception("Failed to start job, an exception occurred")
                ei = sys.exc_info()
                resp = {}
                resp['message'] = "".join(
                    traceback.format_exception_only(*sys.exc_info()[0:2])),
                resp['exception'] = "".join(
                    traceback.format_exception(*sys.exc_info()))

                return JsonResponse(resp, status=400)

        else:
            logger.error("form is invalid, entering debugger")
            from IPython import embed; embed()


class WidgetJobDetail(views.APIView):

    authentication_classes = (SessionAuthentication,
                              BasicAuthentication,
                              URLTokenAuthentication)

    def get(self, request, namespace, report_slug, widget_slug, job_id,
            format=None, status=None):
        logger.debug("WidgetJobDetail GET %s/%s/%s/%s" %
                     (namespace, report_slug, widget_slug, job_id))

        wjob = WidgetJob.objects.get(id=job_id)

        job = wjob.job
        widget = wjob.widget

        if not job.done():
            # job not yet done
            resp = job.json()
        elif job.status == Job.ERROR:
            resp = job.json()
            logger.debug("%s: Job in Error state, deleting Job" % str(wjob))
            wjob.delete()
        else:
            try:
                i = importlib.import_module(widget.module)
                widget_func = i.__dict__[widget.uiwidget].process
                if widget.rows > 0:
                    tabledata = job.values()[:widget.rows]
                else:
                    tabledata = job.values()

                if tabledata is None or len(tabledata) == 0:
                    resp = job.json()
                    resp['status'] = Job.ERROR
                    resp['message'] = "No data returned"
                    logger.debug("%s marked Error: No data returned" %
                                 str(wjob))
                elif hasattr(i, 'authorized') and not i.authorized()[0]:
                    _, msg = i.authorized()
                    resp = job.json()
                    resp['data'] = None
                    resp['status'] = Job.ERROR
                    resp['message'] = msg
                    logger.debug("%s Error: module unauthorized for user %s"
                                 % (str(wjob), request.user))
                elif (hasattr(i, 'authorized') and
                      not Location.objects.all() and
                      not LocationIP.objects.all()):
                    # we are using a maps widget, but have no locations
                    resp = job.json()
                    resp['data'] = None
                    resp['status'] = Job.ERROR
                    msg = '''\
Geolocation data has not been loaded.
See <a href="https://support.riverbed.com/apis/steelscript/appfwk/configuration.html#locations">\
geolocation documentation</a> for more information.'''
                    resp['message'] = msg
                    logger.debug("%s Error: geo location data not loaded.")
                elif status is not None:  # Only status metadata requested
                    resp = job.json()
                else:
                    data = widget_func(widget, job, tabledata)
                    resp = job.json(data)
                    # Cache data before sending it using the
                    # report slug + widget slug as the primary key

                    # check if the report is static
                    report = get_object_or_404(Report, namespace=namespace,
                                               slug=report_slug)

                    if data and report.static:
                        rw_id = '-'.join([namespace, report_slug,
                                          widget_slug])
                        widget_data = WidgetDataCache(report_widget_id=rw_id,
                                                      data=json.dumps(data))
                        widget_data.save()
                        logger.debug("Cached widget %s" % rw_id)
                    logger.debug("%s complete" % str(wjob))

            except:
                logger.exception(("Widget %s (%s) WidgetJob %s, Job %s "
                                 "processing failed") %
                                 (widget.slug, widget.id, wjob.id, job.id))
                resp = job.json()
                resp['status'] = Job.ERROR
                ei = sys.exc_info()
                resp['message'] = str(traceback.format_exception_only(ei[0],
                                                                      ei[1]))

            wjob.delete()

        resp['message'] = cgi.escape(resp['message'])

        try:
            return JsonResponse(resp)
        except:
            logger.error('Failed to generate HttpResponse:\n%s' % str(resp))
            raise
