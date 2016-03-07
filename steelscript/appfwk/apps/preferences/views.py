# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response

from steelscript.appfwk.apps.preferences.forms import UserProfileForm, \
    SystemSettingsForm
from steelscript.appfwk.apps.preferences.models import SystemSettings

logger = logging.getLogger(__name__)


class PreferencesView(APIView):
    """ Display and update user preferences. """
    permission_classes = (IsAuthenticated, )   # no guests
    renderer_classes = (TemplateHTMLRenderer, )

    def get(self, request):
        user = request.user
        if not user.profile_seen:
            user.profile_seen = True
            user.save()
        form = UserProfileForm(instance=user)
        return Response({'form': form}, template_name='preferences.html')

    def post(self, request):
        user = request.user
        form = UserProfileForm(request.DATA, instance=user)
        if form.is_valid():
            form.save()
            if user.timezone_changed:
                request.session['django_timezone'] = user.timezone
                timezone.activate(user.timezone)

            try:
                return HttpResponseRedirect(request.QUERY_PARAMS['next'])
            except KeyError:
                return HttpResponseRedirect(request.META['HTTP_REFERER'])
        else:
            return Response({'form': form}, template_name='preferences.html')


class SystemSettingsView(APIView):
    """ Display and update system settings. """
    renderer_classes = (TemplateHTMLRenderer, )
    permission_classes = (IsAdminUser, )

    def get(self, request):
        instance = SystemSettings.get_system_settings()
        form = SystemSettingsForm(instance=instance)
        return Response({'form': form}, template_name='system_settings.html')

    def post(self, request):
        instance = SystemSettings.get_system_settings()
        form = SystemSettingsForm(request.DATA, instance=instance)
        if form.is_valid():
            form.save()

            try:
                return HttpResponseRedirect(request.QUERY_PARAMS['next'])
            except KeyError:
                return HttpResponseRedirect(request.META['HTTP_REFERER'])
        else:
            return Response({'form': form}, template_name='system_settings.html')
