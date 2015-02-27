# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from re import compile

from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib.auth.models import User
from steelscript.appfwk.apps.preferences.models import PortalUser
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated

from steelscript.appfwk.project.utils import get_request
from steelscript.appfwk.project.settings import REST_FRAMEWORK
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
    """ Authentication class for embedded widget URL. Three view classes are
    using this authentication class, including WidgetView, ReportWidgets and
    WidgetJobDetail in report/views.py. WidgetView class is used to handle
    URLs with auth token in criteria, which is the embedded widget URL. Later
    requests, map to ReportWidgets, WidgetJobList, WidgetJobDetail class, are
    authenticated using the auth token in the header. Note that WidgetView
    class is solely responsible for handling requests with embedded widget URL,
    which is guaranteed to have auth token in the criteria, otherwise it is
    not a valid url to render an HTML page. While ReportWidgets, WidgetJobList
    WidgetJobDetail classes can generate responses to requests not from
    embedding a widget in an HTML, such as polling for status for widgets in a
    report. Therefore, in the case of no auth token in the header for those
    requests, the global authentication methods should be called instead.
    """
    TOKEN_KEY_HEADER = 'HTTP_X_AUTHTOKEN'
    TOKEN_KEY_CRITERIA = 'auth'

    def _is_embed_widget_url(self, request):
        """Return True if the request uses the embed widget url"""

        return request._request.path.find('render') > 0

    def _token_in_header(self, request):
        """Return True if the authentication token is in the header"""

        token = request.META.get(self.TOKEN_KEY_HEADER, 'undefined')
        return token != 'undefined'

    def _token_in_criteria(self, request):
        """Return True if token is in the criteria"""

        return self.TOKEN_KEY_CRITERIA in request.GET.dict()

    def _get_token(self, request):
        """Return token from either Header or criteria fields"""

        return (request.META.get(self.TOKEN_KEY_HEADER, None) or
                request.GET.dict().get(self.TOKEN_KEY_CRITERIA, None))

    def authenticate(self, request):
        if ((not self._is_embed_widget_url(request) and
             self._token_in_header(request))
            or (self._is_embed_widget_url(request) and
                self._token_in_criteria(request))):
            # First check token from database
            token = self._get_token(request)

            try:
                widget = WidgetAuthToken.objects.get(token=token)
            except WidgetAuthToken.DoesNotExist:
                logger.error("Token %s does not exist in db" % token)
                raise exceptions.AuthenticationFailed('Invalid token')

            if ((not request.path.endswith('widgets/') and
                 not request.path.startswith(widget.pre_url)) or
                (request.path.endswith('widgets/') and
                 not widget.pre_url.startswith(request.path))):

                logger.error("request url %s does not match %s in db" %
                             request.path, widget.pre_url)
                raise exceptions.AuthenticationFailed('url does not match')

            try:
                user = PortalUser.objects.get(username=widget.user)
            except User.DoesNotExist:
                logger.error("User %s does not exist" % widget.user.username)
                raise exceptions.AuthenticationFailed('No such user')
            return (user, None)

        elif (not self._is_embed_widget_url(request) and
              not self._token_in_header(request)):
            # Not a request caused by embedded widget html
            # imitate authentication scheme by authenticating
            # the request with each authentication class defined
            # in steelscript.appfwk.project.settings.REST_FRAMEWORK
            # http://www.django-rest-framework.org/api-guide/authentication/
            for class_str in REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']:
                try:
                    # class_str example rest_framework.authentication.CLASS
                    mod_cls = class_str.rsplit('.', 1)
                    # import authentication classes
                    exec('from ' + mod_cls[0] + ' import ' + mod_cls[1])
                    ret = eval(mod_cls[1])().authenticate(request)
                    if ret and len(ret) == 2:
                        return ret
                except:
                    logger.exception("Authenticating using %s Failed" %
                                     class_str)
                    continue

        raise exceptions.AuthenticationFailed('Invalid request')
