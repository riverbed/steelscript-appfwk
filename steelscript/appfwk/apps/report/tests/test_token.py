# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import json

from . import reportrunner


class WidgetTokenTest(reportrunner.ReportRunnerTestCase):

    report = 'token_report'

    def setUp(self):
        super(WidgetTokenTest, self).setUp()
        self.criteria = {'endtime_0': '3/4/2015',
                         'endtime_1': '4:00 pm',
                         'duration': '15min',
                         'resolution': '2min'}
        widgets = self.run_report(self.criteria)
        url = widgets.keys()[0]
        # url="/report/appfwk/<report_slug>/widgets/<widget_slug>/jobs/1/"
        self.base_url = url.rsplit('/', 3)[0]

        self.post_url = self.base_url+'/authtoken/'
        self.criteria_json = json.dumps(self.criteria)
        response = self.client.post(self.post_url,
                                    data={'criteria': self.criteria_json})

        self.token = response.data['auth']

        # log out so that only token is used for authentication
        self.client.logout()

    def run_get_url(self, url=None, code=None):
        response = self.client.get(url)
        assert response.status_code == code

    def test_get_user(self):
        """Test normal GET URL would fail to authenticate due to logged out"""
        self.run_get_url(url='/preferences/user/', code=403)

    def test_normal_render(self):
        get_url = self.base_url + '/render/?auth=%s' % self.token
        self.run_get_url(url=get_url, code=200)

    def test_no_token(self):
        get_url = self.base_url + '/render/'
        self.run_get_url(url=get_url, code=403)

    def test_wrong_token(self):
        get_url = self.base_url + '/render/?auth=wrongtoken'
        self.run_get_url(url=get_url, code=403)

    def test_wrong_url(self):
        no_widget_slug = self.base_url.rsplit('/', 1)[0]
        get_url = no_widget_slug + '/wrong-widget/render/?auth=%s' % self.token
        self.run_get_url(url=get_url, code=403)

    def test_same_token(self):
        """Test when posting token url again with same user, url and criteria,
        the same token should be returned.
        """
        # log back in the server to run the post using same credentials
        super(WidgetTokenTest, self).setUp()
        response = self.client.post(self.post_url,
                                    data={'criteria': self.criteria_json})
        self.assertEqual(response.data['auth'], self.token)

        # different criteria should return different token
        criteria = self.criteria
        criteria['duration'] = '1min'
        criteria_json = json.dumps(criteria)
        response = self.client.post(self.post_url,
                                    data={'criteria': criteria_json})
        self.assertNotEqual(response.data['auth'], self.token)
