# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url

import steelscript.appfwk.apps.plugins.views as views


urlpatterns = patterns(
    'steelscript.appfwk.apps.plugins.views',
    url(r'^$', views.PluginsListView.as_view(), name='plugins-list'),
    url(r'^collect/$', views.PluginsCollectView.as_view(), name='plugins-collect-all'),
    url(r'^(?P<slug>[-\w]+)/$', views.PluginsDetailView.as_view(), name='plugins-detail'),
    url(r'^(?P<slug>[-\w]+)/collect/$', views.PluginsCollectView.as_view(), name='plugins-collect'),
)
