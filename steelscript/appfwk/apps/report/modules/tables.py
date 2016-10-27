# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import re
import logging

from steelscript.common.datastructures import JsonDict
from steelscript.appfwk.apps.report.models import Widget
from steelscript.common import timeutils

logger = logging.getLogger(__name__)


def cleankey(s):
    return re.sub('[:. ]', '_', s)


class BaseTableWidget(object):
    @classmethod
    def base_process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, istime=False, isdate=False):
                self.col = col
                self.key = cleankey(col.name)
                self.dataindex = dataindex
                self.istime = istime
                self.isdate = isdate
        w_keys = []     # Widget column keys in order that matches data
        colinfo = {}    # Map of ColInfo by key
        w_columns = []  # Widget column definitions

        for i, wc in enumerate(job.get_columns()):
            if (widget.options.columns is not None and
                    wc.name not in widget.options.columns):
                continue

            ci = ColInfo(wc, i, wc.istime(), wc.isdate())
            colinfo[ci.key] = ci
            w_keys.append(ci.key)

        # Widget column definitions, make sure this is in the order
        # defined by the widget.options.columns, if specified
        for key in (widget.options.columns or w_keys):
            ci = colinfo[key]
            w_column = {'key': ci.key, 'label': ci.col.label, "sortable": True}

            if ci.col.formatter:
                w_column['formatter'] = ci.col.formatter
                w_column['allowHTML'] = True
            elif ci.col.isnumeric():
                if ci.col.units == ci.col.UNITS_PCT:
                    w_column['formatter'] = 'formatPct'
                else:
                    if ci.col.datatype == ci.col.DATATYPE_FLOAT:
                        w_column['formatter'] = 'formatMetric'
                    elif ci.col.datatype == ci.col.DATATYPE_INTEGER:
                        w_column['formatter'] = 'formatIntegerMetric'
            elif ci.col.istime():
                w_column['formatter'] = 'formatTime'
            elif ci.col.isdate():
                w_column['formatter'] = 'formatDate'
            elif ci.col.datatype == ci.col.DATATYPE_HTML:
                w_column['allowHTML'] = True

            w_columns.append(w_column)

        rows = []

        for rawrow in data:
            row = {}

            for key in w_keys:
                ci = colinfo[key]
                if colinfo[key].istime or colinfo[key].isdate:
                    t = rawrow[ci.dataindex]
                    try:
                        val = timeutils.datetime_to_microseconds(t) / 1000
                    except AttributeError:
                        val = t * 1000
                else:
                    val = rawrow[ci.dataindex]

                row[key] = val

            rows.append(row)

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "columns": w_columns,
            "data": rows
        }

        return data


class TableWidget(BaseTableWidget):
    @classmethod
    def create(cls, section, table, title, width=6, height=300, rows=1000,
               cols=None, info=True, paging=False, row_chooser=False,
               searching=True):
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

        """
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        w.options = JsonDict(columns=cols,
                             info=info,
                             paging=paging,
                             row_chooser=row_chooser,
                             searching=searching)
        w.save()
        w.tables.add(table)

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
                 'title': c['label']} for c in data['columns']]

        data['columns'] = cols
        data['options'] = options
        return data


class PivotTableWidget(BaseTableWidget):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               cols=None, rows=1000):
        """Create a widget displaying data in a pivot table.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 1000)
        :param list cols: List of columns by name to include.  If None,
            the default, include all data columns.

        """
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        w.options = JsonDict(columns=cols)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        data = cls.base_process(widget, job, data)
        return data
