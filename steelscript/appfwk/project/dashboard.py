"""
This file was generated with the customdashboard management command, it
contains the two classes for the main dashboard and app index dashboard.
You can customize these classes as you want.

"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from admin_tools.dashboard import modules, Dashboard, AppIndexDashboard
from admin_tools.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for SteelScript Application Framework.
    """
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            _('Quick links'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_('Return to site'), '/'],
                [_('Change password'),
                 reverse('%s:password_change' % site_name)],
                [_('Log out'), reverse('%s:logout' % site_name)],
            ]
        ))

        # append an app list module for "Administration"
        self.children.append(modules.AppList(
            _('Administration'),
            models=(
                'pinax.announcements.*',
                'steelscript.appfwk.apps.hitcount.*',
                'steelscript.appfwk.apps.preferences.*',
                'steelscript.appfwk.apps.devices.*',
                'steelscript.appfwk.apps.pcapmgr.*',
                'steelscript.appfwk.apps.geolocation.*',
                'steelscript.appfwk.apps.report.*',
                'steelscript.*.appfwk.*',
            ),
        ))

        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            _('System Models'),
            models=('steelscript.appfwk.apps.*',),
            exclude=('steelscript.appfwk.apps.devices.*',
                     'steelscript.appfwk.apps.pcapmgr.*',
                     'steelscript.appfwk.apps.preferences.*',
                     'steelscript.appfwk.apps.geolocation.*',
                     'steelscript.appfwk.apps.report.*',)
        ))

        # append a recent actions module
        self.children.append(modules.RecentActions(_('Recent Actions'), 5))

        # append a feed module
#        self.children.append(modules.Feed(
#            _('Latest Django News'),
#            feed_url='http://www.djangoproject.com/rss/weblog/',
#            limit=5
#        ))

        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Support'),
            children=[
                {
                    'title': _('SteelScript Community Page'),
                    'url': 'https://splash.riverbed.com/steelscript',
                    'external': True,
                },
                {
                    'title': _('SteelScript on Github'),
                    'url': 'https://github.com/riverbed/steelscript',
                    'external': True,
                },
                {
                    'title': _('SteelScript Documentation'),
                    'url': 'http://support.riverbed.com/apis/steelscript',
                    'external': True,
                    },
                {
                    'title': _('Django documentation'),
                    'url': 'http://docs.djangoproject.com/',
                    'external': True,
                },
            ]
        ))


class CustomAppIndexDashboard(AppIndexDashboard):
    """
    Custom app index dashboard for steelscript-appfwk.
    """

    # we disable title because its redundant with the model list module
    title = ''

    def __init__(self, *args, **kwargs):
        AppIndexDashboard.__init__(self, *args, **kwargs)

        # append a model list module and a recent actions module
        self.children += [
            modules.ModelList(self.app_title, self.models),
            modules.RecentActions(
                _('Recent Actions'),
                include_list=self.get_app_content_types(),
                limit=5
            )
        ]

    def init_with_context(self, context):
        """
        Use this method if you need to access the request context.
        """
        return super(CustomAppIndexDashboard, self).init_with_context(context)
