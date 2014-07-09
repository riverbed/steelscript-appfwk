# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, include, url
from django.http import HttpResponseRedirect

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from django.conf import settings

from steelscript.appfwk.apps.datasource.models import Job
Job.flush_incomplete()

urlpatterns = patterns('',
    (r'^favicon\.ico$', lambda x: HttpResponseRedirect('/static/images/favicon.ico')),
    url(r'^$', lambda x: HttpResponseRedirect('/report')),
    url(r'^report/', include('steelscript.appfwk.apps.report.urls')),
    url(r'^devices/', include('steelscript.appfwk.apps.devices.urls')),
    url(r'^data/', include('steelscript.appfwk.apps.datasource.urls')),
    url(r'^geolocation/', include(
        'steelscript.appfwk.apps.geolocation.urls')),
    url(r'^help/', include('steelscript.appfwk.apps.help.urls')),
    url(r'^preferences/', include(
        'steelscript.appfwk.apps.preferences.urls')),
    url(r'^plugins/', include('steelscript.appfwk.apps.plugins.urls')),

    # third party packages
    url(r'^announcements/', include('announcements.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin_tools/', include('admin_tools.urls')),

    # Account login
    url(r'^accounts/login/$', 'django.contrib.auth.views.login',
        {'template_name': 'login.html'}),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        {'next_page': '/accounts/login'}),
    url(r'^accounts/password_change/$', 'django.contrib.auth.views.password_change',
        {'post_change_redirect': '/preferences/user',
         'template_name': 'password_change_form.html'}),
)
