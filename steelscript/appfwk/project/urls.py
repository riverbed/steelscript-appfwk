# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.http import HttpResponseRedirect


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^favicon\.ico$', lambda x: HttpResponseRedirect('/static/images/favicon.ico')),
    url(r'^$', lambda x: HttpResponseRedirect('/report')),
    url(r'^report/', include('steelscript.appfwk.apps.report.urls')),
    url(r'^devices/', include('steelscript.appfwk.apps.devices.urls')),
    url(r'^pcapmgr/', include('steelscript.appfwk.apps.pcapmgr.urls')),
    url(r'^data/', include('steelscript.appfwk.apps.datasource.urls')),
    url(r'^alerting/', include('steelscript.appfwk.apps.alerting.urls')),
    url(r'^geolocation/', include(
        'steelscript.appfwk.apps.geolocation.urls')),
    url(r'^help/', include('steelscript.appfwk.apps.help.urls')),
    url(r'^preferences/', include(
        'steelscript.appfwk.apps.preferences.urls')),
    url(r'^plugins/', include('steelscript.appfwk.apps.plugins.urls')),
    url(r'^jobs/', include('steelscript.appfwk.apps.jobs.urls')),
    url(r'^logs/', include('steelscript.appfwk.apps.logviewer.urls')),
    url(r'^announcements/', include(
        'pinax.announcements.urls', namespace='pinax_announcements')),
    url(r'^metrics/', include('steelscript.appfwk.apps.metrics.urls')),

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
    url(r'^tagging_autocomplete/', include('tagging_autocomplete.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
