# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from steelscript.appfwk.apps.datasource.models import \
    DatasourceTable, TableQueryBase
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.devices.forms import fields_add_device_selection


logger = logging.getLogger(__name__)


class SharepointTable(DatasourceTable):
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'site_url': '',
                     'list_name': ''}

    _query_class = 'SharepointQuery'

    def post_process_table(self, field_options):
        fields_add_device_selection(self,
                                    keyword='sharepoint_device',
                                    label='Sharepoint',
                                    module='sharepoint_device',
                                    enabled=True)


class SharepointQuery(TableQueryBase):

    def run(self):
        """ Main execution method
        """

        criteria = self.job.criteria

        if criteria.sharepoint_device == '':
            logger.debug('%s: No sharepoint device selected' % self.table)
            self.job.mark_error("No Sharepoint Device Selected")
            return False

        sp = DeviceManager.get_device(criteria.sharepoint_device)

        site = sp.get_site_object(self.table.options.site_url)

        site_instance = site.lists[self.table.options.list_name]
        fields = [tc.name for tc in self.table.get_columns(synthetic=False)]

        self.data = []
        for row in site_instance.rows:
            d = [getattr(row, f) for f in fields]
            self.data.append(d)

        logger.info("SharepointTable job %s returning %s data" %
                    (self.job, len(self.data)))

        return True
