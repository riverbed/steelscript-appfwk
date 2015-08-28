# Copyright (c) 2015 Riverbed Technology, Inc.
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

    def run_get_url(self, url=None, code=None):
        response = self.client.get(url)
        assert response.status_code == code


class SimpleWidgetTokenTest(WidgetTokenTest):

    report = 'token_report'

    def setUp(self):
        super(SimpleWidgetTokenTest, self).setUp()

        # log out so that only token is used for authentication
        self.client.logout()

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


class EditFieldsWidgetTokenTest(WidgetTokenTest):

    def test_normal_render(self):
        self.post_url = self.base_url + '/%s/editfields/' % self.token
        edit_fields = json.dumps(['endtime_0', 'duration'])
        self.client.post(self.post_url, data={'edit_fields': edit_fields})

        get_url = (self.base_url +
                   '/render/?auth=%s&endtime_0=1&duration=2d' % self.token)
        self.run_get_url(get_url, 200)

        get_url = (self.base_url +
                   '/render/?auth=%s&endtime=1' % self.token)
        self.run_get_url(get_url, 403)

        get_url = (self.base_url +
                   '/render/?auth=%s&endtime_1=1&resolution=2d' % self.token)
        self.run_get_url(get_url, 403)


class ReportEditorTest(WidgetTokenTest):

    def setUp(self):
        super(ReportEditorTest, self).setUp()
        # base_url = /report/appfwk/token_report
        self.base_url = self.base_url.rsplit('/', 2)[0]
        with open('reports/token_report.py', 'r') as f:
            self.text = f.readlines()

    def test_report_save(self):
        url = self.base_url + '/edit/'
        response = self.client.post(url, data={'text': self.text})
        self.assertEqual(response.status_code, 200)
