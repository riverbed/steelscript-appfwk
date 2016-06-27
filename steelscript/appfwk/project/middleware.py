# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from re import compile

from django.http import HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import resolve

from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated

from steelscript.appfwk.project.utils import get_request
from steelscript.appfwk.apps.report.models import WidgetAuthToken

logger = logging.getLogger(__name__)

#
# Global authentication locks
# adapted from stack overflow question
# http://tinyurl.com/kaeqg37
#
def get_exempts():
    exempts = [compile(settings.LOGIN_URL.lstrip('/'))]
    if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
        exempts += [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]
    return exempts


class LoginRequiredMiddleware(object):
    """
    Middleware that requires a user to be authenticated to view any page other
    than reverse(LOGIN_URL_NAME). Exemptions to this requirement can optionally
    be specified in settings via a list of regular expressions in
    LOGIN_EXEMPT_URLS (which you can copy from your urls.py).

    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """
    def process_request(self, request):
        assert hasattr(request, 'user'), "The Login Required middleware\
requires authentication middleware to be installed. Edit your\
MIDDLEWARE_CLASSES setting to insert\
'django.contrib.auth.middlware.AuthenticationMiddleware'. If that\
doesn't work, ensure your TEMPLATE_CONTEXT_PROCESSORS setting includes\
'django.core.context_processors.auth'."
        if not request.user.is_authenticated():
            path = request.path.lstrip('/')
            if not any(m.match(path) for m in get_exempts()):
                return HttpResponseRedirect(
                    settings.LOGIN_URL + "?next=" + request.path)


#
# Custom exception handling for Django REST Framework
#
def authentication_exception_handler(exc):
    """ Returns redirect to login page only when requesting HTML. """
    request = get_request()

    if (isinstance(exc, NotAuthenticated) and
            'text/html' in request.negotiator.get_accept_list(request)):
        return HttpResponseRedirect(settings.LOGIN_URL + "?next=" + request.path)

    response = exception_handler(exc)

    return response


class URLTokenAuthentication(authentication.BaseAuthentication):
    """ Authentication class for embedded widget URL.

    Four view classes are using this authentication class, including
    WidgetView, ReportWidgets, WidgetJobsList, and WidgetJobDetail
    in report/views.py.

    WidgetView class is used to handle URLs with auth token in URL params,
    which is the embedded widget URL. Later requests, which map to
    ReportWidgets, WidgetJobList, WidgetJobDetail class, are authenticated
    using the auth token in the header.

    Note that WidgetView class is solely responsible for handling requests
    with embedded widget URL, which is required to have auth token in URL
    params, otherwise it is not a valid url to render an HTML page.
    While ReportWidgets, WidgetJobList, WidgetJobDetail classes can generate
    responses to requests not from embedding a widget in an HTML, such as
    polling for status for widgets in a report. Therefore, in the case of
    no auth token in the header of requests, the global authentication methods
    should be called.
    """

    TOKEN_KEY_HEADER = 'HTTP_X_AUTHTOKEN'
    TOKEN_KEY_URL_PARAMS = 'auth'

    def _is_embed_widget_url(self, request):
        """Return True if the request uses the embed widget url"""

        return resolve(request.path).url_name == 'widget-stand-alone'

    def _token_in_header(self, request):
        """Return True if the authentication token is in the header"""

        token = request.META.get(self.TOKEN_KEY_HEADER, 'undefined')
        return token != 'undefined'

    def _token_in_url_params(self, request):
        """Return True if token is in URL parameters"""

        return self.TOKEN_KEY_URL_PARAMS in request.GET.dict()

    def _is_report_widgets_url(self, request):
        """Return True if the request's path follows the pattern of
        'report-widgets' url defined in report/urls.py, shown as:
        '^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/widgets/'
        """

        return resolve(request.path).url_name == 'report-auto-view'

    def authenticate(self, request):
        if (self._is_embed_widget_url(request) and
                self._token_in_url_params(request)):
            token = request.GET.dict().get(self.TOKEN_KEY_URL_PARAMS)

        elif (not self._is_embed_widget_url(request) and
              self._token_in_header(request)):
            token = request.META.get(self.TOKEN_KEY_HEADER)

        elif (self._is_embed_widget_url(request) or
              not settings.GUEST_USER_ENABLED):
            # no token provided, and guest access not allowed
            raise exceptions.AuthenticationFailed('No valid token')

        else:
            # no token and guest access enabled
            return None

        try:
            token_obj = WidgetAuthToken.objects.get(token=token)
        except WidgetAuthToken.DoesNotExist:
            logger.error("Token %s does not exist in db" % token)
            raise exceptions.AuthenticationFailed('Invalid token')

        # The below boolean expression ensures if the request is to get widgets
        # then its path needs to be the prefix of the token object's pre_url.
        # otherwise the request's path must have the token object's pre_url
        # as prefix.

        # For example, the pre_url of one token object is as follows:
        # /report/netprofiler/netprofiler/widgets/overall-traffic-1-1/
        # There are two kinds of paths from requests that are authenticated
        # in this method, one is the report widgets request, with path as a
        # prefix of the pre_url of the token object, shown as:
        # /report/netprofiler/netprofiler/widgets/,
        # the other one consists of requests with paths with the pre_url of
        # the token object as prefix, i.e. embed widget request'path is as:
        # /report/netprofiler/netprofiler/widgets/overall-traffic-1-1/render/
        # widget joblist path is shown as:
        # /report/netprofiler/netprofiler/widgets/overall-traffic-1-1/jobs/
        # widget job status path is shown as:
        # /report/netprofiler/netprofiler/widgets/overall-traffic-1-1/jobs/1/
        if ((not self._is_report_widgets_url(request) and
             not request.path.startswith(token_obj.pre_url)) or
            (self._is_report_widgets_url(request) and
             not token_obj.pre_url.startswith(request.path))):

            logger.error("request url %s does not match %s in db" %
                         (request.path, token_obj.pre_url))
            raise exceptions.AuthenticationFailed('url does not match')

        user = token_obj.user

        token_obj.save()
        return (user, None)
