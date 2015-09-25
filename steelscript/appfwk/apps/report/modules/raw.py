# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import datetime
import pytz

from steelscript.common.timeutils import datetime_to_seconds

from steelscript.appfwk.apps.report.models import Widget

import logging
logger = logging.getLogger(__name__)


class TableWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=1000, height=300):
        """Create a widget displaying data in a two dimensional table.

        This is similar to ``yui3.TableWidget`` except the key and data
        values are minimally formatted to show raw data values.  Usually
        only used for testing and debug.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 10)

        """
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        newdata = []
        for row in data:
            newrow = []
            for col in row:
                if isinstance(col, datetime.datetime):
                    if col.tzinfo is None:
                        col = col.replace(tzinfo=pytz.utc)
                    col = datetime_to_seconds(col)
                newrow.append(col)
            newdata.append(newrow)

        return newdata
