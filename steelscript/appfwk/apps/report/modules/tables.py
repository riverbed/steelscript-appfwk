# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import re
import logging

from steelscript.appfwk.apps.report.models import Widget, UIWidgetHelper
from steelscript.common import timeutils

logger = logging.getLogger(__name__)


def clean_key(s):
    # remove unwanted characters from string `s`
    return re.sub('[:. ]', '_', s)


class BaseTableWidget(object):
    @classmethod
    def base_process(cls, widget, job, data):
        helper = UIWidgetHelper(widget, job)

        rows = []

        for rawrow in data:
            row = {}

            for col in helper.colmap.values():
                if col.istime or col.isdate:
                    t = rawrow[col.dataindex]
                    try:
                        val = timeutils.datetime_to_microseconds(t) / 1000
                    except AttributeError:
                        val = t * 1000
                else:
                    val = rawrow[col.dataindex]
                row[col.key] = val
            rows.append(row)

        column_defs = [
            c.to_json('key', 'label', 'sortable', 'formatter', 'allow_html')
            for c in helper.colmap.values()
        ]

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "columns": column_defs,
            "data": rows
        }

        return data


class TableWidget(BaseTableWidget):
    @classmethod
    def create(cls, section, table, title, width=6, height=300, rows=1000,
               cols=None, info=True, paging=False, row_chooser=False,
               searching=False, stack_widget=False):
        """Create a widget displaying data in a pivot table.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300).
        :param int rows: Number of rows to display (default 1000)
        :param list cols: List of columns by name to include.  If None,
            the default, include all data columns.

        Data Table Options:
        :param bool info: Optionally display "Showing X of Y entries"
        :param bool paging: Optionally display page number chooser.
            If disabled, scrolling will instead be enabled and `row_chooser`
            will be set to False.
        :param bool row_chooser: Optionally choose how many rows to display.
            Will be disabled if paging option is disabled.
        :param bool searching: Optionally display search box at top.
        :param bool stack_widget: stack this widget below the previous one.

        """
        options = {'columns': cols,
                   'info': info,
                   'paging': paging,
                   'row_chooser': row_chooser,
                   'searching': searching}

        Widget.create(section=section, table=table, title=title,
                      rows=rows, width=width, height=height,
                      module=__name__, uiwidget=cls.__name__,
                      options=options, stack_widget=stack_widget)

    @classmethod
    def process(cls, widget, job, data):
        data = cls.base_process(widget, job, data)

        options = dict(widget.options)
        options['lengthChange'] = options.pop('row_chooser', True)
        options['scrollY'] = True
        if not options['paging']:
            options['lengthChange'] = False

        # if widget height was set to 0, reset some options to take
        # advantage of the non-fixed height
        if widget.height == 0:
            options['lengthChange'] = True
            options['scrollY'] = False
            options['paging'] = True

        # reformat columns
        cols = [{'data': c['key'],
                 'title': c['label'],
                 'formatter': c['formatter']} for c in data['columns']]

        data['columns'] = cols
        data['options'] = options
        return data


class PivotTableWidget(BaseTableWidget):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               cols=None, rows=1000, stack_widget=False):
        """Create a widget displaying data in a pivot table.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300).
            For this interactive widget, the best option is `0` - this
            will make the widget size dynamic as new pivots are chosen.  Any
            other height will result in scrolling withing the widget pane.
        :param int rows: Number of rows to display (default 1000)
        :param list cols: List of columns by name to include.  If None,
            the default, include all data columns.
        :param bool stack_widget: stack this widget below the previous one.

        """
        options = {'columns': cols}

        Widget.create(section=section, table=table, title=title,
                      rows=rows, width=width, height=height,
                      module=__name__, uiwidget=cls.__name__,
                      options=options, stack_widget=stack_widget)

    @classmethod
    def process(cls, widget, job, data):
        data = cls.base_process(widget, job, data)
        return data
