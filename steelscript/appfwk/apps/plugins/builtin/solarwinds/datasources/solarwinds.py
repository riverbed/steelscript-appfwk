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


class SolarwindsTable(DatasourceTable):
    class Meta:
        proxy = True

    _query_class = 'SolarwindsQuery'

    def post_process_table(self, field_options):
        fields_add_device_selection(self,
                                    keyword='solarwinds_device',
                                    label='Solarwinds',
                                    module='solarwinds',
                                    enabled=True)


class SolarwindsQuery(TableQueryBase):

    def run(self):
        """ Main execution method
        """

        criteria = self.job.criteria

        if criteria.solarwinds_device == '':
            logger.debug('%s: No solarwinds device selected' % self.table)
            self.job.mark_error("No Solarwinds Device Selected")
            return False

        sw = DeviceManager.get_device(criteria.solarwinds_device)

        # TODO add queries
        self.data = None

        logger.info("SolarwindsTable job %s returning %s data" %
                    (self.job, len(self.data)))
        return True
