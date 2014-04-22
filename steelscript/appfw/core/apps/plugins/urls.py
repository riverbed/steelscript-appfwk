# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, url
import steelscript.appfw.core.apps.plugins.views as views

urlpatterns = patterns(
    'steelscript.appfw.core.apps.plugins.views',
    url(r'^$', views.PluginsListView.as_view(), name='plugins-list'),
    url(r'^(?P<slug>[-\w]+)/$', views.PluginsDetailView.as_view(), name='plugins-detail'),
)
