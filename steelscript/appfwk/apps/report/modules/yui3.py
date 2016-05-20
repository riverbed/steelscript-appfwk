# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import re
import math
import logging

from steelscript.common import timeutils
from steelscript.common.datastructures import JsonDict
from steelscript.appfwk.libs.nicescale import NiceScale
from steelscript.appfwk.apps.report.models import Axes, Widget

logger = logging.getLogger(__name__)


def cleankey(s):
    return re.sub('[:. ]', '_', s)


class TableWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6,
               cols=None, rows=1000, height=300, stack_widget=False):
        """Create a widget displaying data in a two dimensional table.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 1000)
        :param list cols: List of columns by name to include.  If None,
            the default, include all data columns.
        :param bool stack_widget: stack this widget below the previous one.

        """
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__,
                   stack_widget=stack_widget)
        w.compute_row_col()
        w.options = JsonDict(columns=cols)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
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
        w_columns = []
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


class PieWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300,
               stack_widget=False):
        """Create a widget displaying data in a pie chart.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 10)
        :param bool stack_widget: stack this widget below the previous one.

        The labels are taken from the Table key column (the first key,
        if the table has multiple key columns defined).  The pie
        widget values are taken from the sort column.

        """
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__,
                   stack_widget=stack_widget)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns()
                   if col.iskey is True]

        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined"
                             % str(table))

        if table.sortcols is None:
            raise ValueError("Table %s does not have a sort column defined" %
                             str(table))

        w.options = JsonDict(key=keycols[0],
                             value=table.sortcols[0])
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        columns = job.get_columns()

        col_names = [c.name for c in columns]
        catcol = [c for c in columns if c.name == widget.options.key][0]
        col = [c for c in columns if c.name == widget.options.value][0]

        series = []
        series.append({"categoryKey": catcol.name,
                       "categoryDisplayName": catcol.label,
                       "valueKey": col.name,
                       "valueDisplayName": col.label
                       })

        rows = []

        if len(data) > 0:
            for rawrow in data:
                row = dict(zip(col_names, rawrow))
                r = {catcol.name: row[catcol.name],
                     col.name: row[col.name]}
                rows.append(r)
        else:
            # create a "full" pie to show something
            rows = [{catcol.name: 1,
                     col.name: 1}]

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": "pie",
            "categoryKey": catcol.name,
            "dataProvider": rows,
            "seriesCollection": series,
            "legend": {"position": "right"}
        }

        return data


class TimeSeriesWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               stacked=False, cols=None, altaxis=None, bar=False,
               stack_widget=False):
        """Create a widget displaying time-series data in a line or bar chart

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param bool stacked: If True, show multiple series as stacked
        :param list cols: List of columns by name to graph.  If None,
            the default, graph all data columns.
        :param list altaxis: List of columns to graph using the
            alternate Y-axis
        :param bool bar: If True, show time series in a bar chart.
        :param bool stack_widget: stack this widget below the previous one.

        As an example, the following will graph four columns of data::

            section.add_widget(yui3.TimeSeriesWidget, 'Bytes and Packets',
                               stacked=True, width=12, height=450,
                               cols=['bytes', 'rtxbytes',
                                     'packets', 'rtxpackets'],
                               altaxis=['packets', rtxpackets'])

        The columns 'bytes' and 'rtxbytes' will be graphed against the left
        Y-axis, 'packets' and 'rtxpackets' on the right (alternate) Y-axis.

        """

        w = Widget(section=section, title=title, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__,
                   stack_widget=stack_widget)
        w.compute_row_col()
        timecols = [col.name for col in table.get_columns()
                    if col.istime() or col.isdate()]
        if len(timecols) == 0:
            raise ValueError("Table %s must have a datatype 'time' column for "
                             "a timeseries widget" % str(table))

        w.options = JsonDict(columns=cols,
                             altaxis=altaxis,
                             stacked=stacked,
                             bar=bar)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, axis,
                         istime=False, isdate=False):
                self.col = col
                self.key = cleankey(col.name)
                self.dataindex = dataindex
                self.axis = axis
                self.istime = istime
                self.isdate = isdate
        t_cols = job.get_columns()
        colinfo = {}  # map by widget key

        # columns of None is a special case, just use all
        # defined columns other than time
        if widget.options.columns is None:
            valuecolnames = [col.name for col in t_cols
                             if not col.istime() and not col.isdate()]
        else:
            valuecolnames = widget.options.columns

        # Column keys are the 'cleaned' column names
        w_keys = [cleankey(n) for n in valuecolnames]

        # Retrieve the desired value columns
        # ...and the indices for the value values
        # (as the 'data' has *all* columns)
        time_colinfo = None
        for i, c in enumerate(t_cols):
            if c.istime():
                ci = ColInfo(c, i, -1, istime=True)
                time_colinfo = ci
            elif c.isdate():
                ci = ColInfo(c, i, -1, isdate=True)
                time_colinfo = ci
            elif c.name in valuecolnames:
                if c.isnumeric():
                    ci = ColInfo(c, i, -1, istime=False, isdate=False)
                else:
                    raise KeyError(
                        "Cannot graph non-numeric data in timeseries widget: "
                        "column {0}".format(c.name))

            colinfo[ci.key] = ci

        if widget.options.altaxis:
            altaxis = widget.options.altaxis
            axes_def = {'0': {'position': 'left',
                              'columns': [col for col in valuecolnames
                                          if col not in altaxis]},
                        '1': {'position': 'right',
                              'columns': [col for col in valuecolnames
                                          if col in altaxis]}
                        }
        else:
            axes_def = {'0': {'position': 'left',
                              'columns': valuecolnames}}
        w_series = []
        axes = Axes(axes_def)

        # Setup the time axis
        w_axes = {"time": {"keys": ["time"],
                           "position": "bottom",
                           "type": "time",
                           "styles": {"label": {"fontSize": "8pt",
                                                "rotation": "-45"}}}}

        # Create a better time format depending on t0/t1
        t_dataindex = time_colinfo.dataindex

        t0 = data[0][t_dataindex]
        t1 = data[-1][t_dataindex]
        if not hasattr(t0, 'utcfromtimestamp'):
            t0 = timeutils.sec_string_to_datetime(t0)
            t1 = timeutils.sec_string_to_datetime(t1)

        total_seconds = timeutils.timedelta_total_seconds(t1 - t0)
        if total_seconds < 2:
            w_axes['time']['formatter'] = 'formatTimeMs'
        elif total_seconds < 120:
            w_axes['time']['labelFormat'] = '%k:%M:%S'
        elif total_seconds < (24 * 60 * 60):
            w_axes['time']['labelFormat'] = '%k:%M'
        elif time_colinfo.isdate:
            w_axes['time']['formatter'] = 'formatDate'
        else:
            w_axes['time']['labelFormat'] = '%D %k:%M'

        # Setup the other axes, checking the axis for each column
        for w_key in w_keys:
            # Need to interate the valuecolnames array to preserve order
            ci = colinfo[w_key]

            w_series.append({"xKey": "time",
                             "xDisplayName": "Time",
                             "yKey": ci.key,
                             "yDisplayName": ci.col.label,
                             "styles": {"line": {"weight": 1},
                                        "marker": {"height": 3,
                                                   "width": 3}}})

            ci.axis = axes.getaxis(ci.col.name)
            axis_name = 'axis' + str(ci.axis)
            if axis_name not in w_axes:
                w_axes[axis_name] = {"type": "numeric",
                                     "position": axes.position(ci.axis),
                                     "keys": []
                                     }

            w_axes[axis_name]['keys'].append(ci.key)

        # Output row data
        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        stacked = widget.options.stacked
        # Iterate through all rows if input data
        for rawrow in data:
            t = rawrow[t_dataindex]
            try:
                t = timeutils.datetime_to_microseconds(t) / 1000
            except AttributeError:
                t = t * 1000

            row = {'time': t}
            rowmin = {}
            rowmax = {}
            for ci in colinfo.values():
                if ci.istime or ci.isdate:
                    continue
                a = ci.axis
                val = rawrow[ci.dataindex]
                row[ci.key] = val if val != '' else None

                # If stacked and there is only one value, use that
                # value as the rowmin.  If stacked and there is more than
                # one value for the axis, use a floor of 0 to give proper
                # context.
                if a not in rowmin:
                    rowmin[a] = val if val != '' else 0
                    rowmax[a] = val if val != '' else 0
                else:
                    rowmin[a] = (0 if stacked
                                 else min(rowmin[a], val))
                    rowmax[a] = ((rowmax[a] + val) if stacked
                                 else max(rowmax[a], val))

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a],
                                                                    rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a],
                                                                    rowmax[a])

            rows.append(row)

        # Setup the scale values for the axes
        for ci in colinfo.values():
            if ci.istime or ci.isdate:
                continue

            axis_name = 'axis' + str(ci.axis)

            if minval and maxval:
                n = NiceScale(minval[ci.axis], maxval[ci.axis])

                w_axes[axis_name]['minimum'] = "%.10f" % n.nicemin
                w_axes[axis_name]['maximum'] = "%.10f" % n.nicemax
                w_axes[axis_name]['tickExponent'] = math.log10(n.tickspacing)
                w_axes[axis_name]['styles'] = {
                    'majorUnit': {'count': n.numticks}
                }
            else:
                # empty data which would result in keyError above
                w_axes[axis_name]['minimum'] = "0"
                w_axes[axis_name]['maximum'] = "1"
                w_axes[axis_name]['tickExponent'] = 1
                w_axes[axis_name]['styles'] = {'majorUnit': {'count': 1}}

            if ci.col.units == ci.col.UNITS_PCT:
                w_axes[axis_name]['formatter'] = 'formatPct'
            else:
                w_axes[axis_name]['formatter'] = 'formatMetric'

        if stacked:
            charttype = "area"
        elif widget.options.bar:
            charttype = "column"
        else:
            charttype = "combo"

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": charttype,
            "stacked": stacked,
            "dataProvider": rows,
            "seriesCollection": w_series,
            "axes": w_axes,
            "legend": {"position": "bottom",
                       "fontSize": "8pt",
                       "styles": {"gap": 0}},
            "interactionType": "planar"
        }

        # logger.debug("data:\n\n%s\n" % data)
        return data


class ChartWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300,
               keycols=None, valuecols=None, charttype='line', dynamic=False,
               stack_widget=False):
        """Create a widget displaying data as a chart.

        This class is typically not used directly, but via LineWidget
        or BarWidget subclasses

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 10)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: List of data columns to graph
        :param str charttype: Type of chart, defaults to 'line'.  This may be
           any YUI3 'type'
        :param bool dynamic: columns will be added later from criteria if True
        :param bool stack_widget: stack this widget below the previous one.

        """
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__,
                   stack_widget=stack_widget)
        w.compute_row_col()
        if keycols is None:
            keycols = [col.name for col in table.get_columns()
                       if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" %
                             str(table))

        if valuecols is None:
            valuecols = [col.name for col in table.get_columns()
                         if col.iskey is False]
        w.options = JsonDict(dict={'keycols': keycols,
                                   'columns': valuecols,
                                   'axes': None,
                                   'charttype': charttype,
                                   'dynamic': dynamic})
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, axis):
                self.col = col
                self.dataindex = dataindex
                self.axis = axis

        all_cols = job.get_columns()

        # The category "key" column -- this is the column shown along the
        # bottom of the bar widget
        keycols = [c for c in all_cols if c.name in widget.options.keycols]

        # columns of '*' is a special case, just use all
        # defined columns other than time
        if widget.options.columns == '*' or widget.options.dynamic:
            cols = [c for c in all_cols if not c.iskey]
        else:
            # The value columns - one set of bars for each
            cols = [c for c in all_cols if c.name in widget.options.columns]

        axes = Axes(widget.options.axes)

        # Array of data series definitions yui3 style
        series = []

        # Array of axis definitions yui3 style
        catname = '-'.join([k.name for k in keycols])
        w_axes = {catname: {"keys": [catname],
                            "position": "bottom",
                            "styles": {"label": {"rotation": -60}}}}

        # Map of column info by column name
        colmap = {}

        # Add keycols to the colmap
        for i, c in enumerate(all_cols):
            if c not in keycols:
                continue
            ci = ColInfo(c, i, axes.getaxis(c.name))
            colmap[c.name] = ci

        for i, c in enumerate(all_cols):
            # Rest of this is for data cols only
            if c not in cols:
                continue

            ci = ColInfo(c, i, axes.getaxis(c.name))
            colmap[c.name] = ci

            series.append({"xKey": '-'.join([k.name for k in keycols]),
                           "xDisplayName": ','.join([k.label
                                                     for k in keycols]),
                           "yKey": c.name,
                           "yDisplayName": c.label,
                           "styles": {"line": {"weight": 1},
                                      "marker": {"height": 6,
                                                 "width": 20}}})

            # The rest compute axis min/max for datavalues, so skip keys
            if c.iskey:
                continue

            axis_name = 'axis' + str(ci.axis)
            if axis_name not in w_axes:
                w_axes[axis_name] = {"type": "numeric",
                                     "position": ("left" if (ci.axis == 0)
                                                  else "right"),
                                     "keys": []}

            w_axes[axis_name]['keys'].append(c.name)

        # Array of actual data yui3 style.  Each row is a dict of key->value
        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        stacked = False  # XXXCJ

        for rawrow in data:
            row = {}
            rowmin = {}
            rowmax = {}

            # collect key values
            keyvals = []
            for c in colmap.values():
                if not c.col.iskey:
                    continue
                keyvals.append(rawrow[c.dataindex])
            row[catname] = ','.join(str(k) for k in keyvals)

            # collect the data values
            for c in colmap.values():
                if c.col.iskey:
                    continue

                # Set the value
                val = rawrow[c.dataindex]
                row[c.col.name] = val

                a = c.axis
                if c.axis not in rowmin:
                    rowmin[a] = val
                    rowmax[a] = val
                else:
                    rowmin[a] = ((rowmin[a] + val) if stacked
                                 else min(rowmin[a], val))
                    rowmax[a] = ((rowmax[a] + val) if stacked
                                 else max(rowmax[a], val))

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a],
                                                                    rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a],
                                                                    rowmax[a])
            rows.append(row)

        # Build up axes
        for c in colmap.values():
            if c.col.iskey:
                continue

            axis_name = 'axis' + str(c.axis)

            if minval and maxval:
                n = NiceScale(minval[c.axis], maxval[c.axis])

                w_axes[axis_name]['minimum'] = "%.10f" % n.nicemin
                w_axes[axis_name]['maximum'] = "%.10f" % n.nicemax
                w_axes[axis_name]['tickExponent'] = math.log10(n.tickspacing)
                w_axes[axis_name]['styles'] = {
                    'majorUnit': {'count': n.numticks}
                }
            else:
                # empty data which would result in keyError above
                w_axes[axis_name]['minimum'] = "0"
                w_axes[axis_name]['maximum'] = "1"
                w_axes[axis_name]['tickExponent'] = 1
                w_axes[axis_name]['styles'] = {'majorUnit': {'count': 1}}

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": widget.options.charttype,
            "categoryKey": catname,
            "dataProvider": rows,
            "seriesCollection": series,
            "axes": w_axes,
            "legend": {"position": "bottom",
                       "fontSize": "8pt",
                       "styles": {"gap": 0}}
        }

        return data


class BarWidget(ChartWidget):
    @classmethod
    def create(cls, *args, **kwargs):
        """Create a widget displaying data as a bar chart.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 10)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: List of data columns to graph
        :param str charttype: Type of chart, defaults to 'line'.  This may be
           any YUI3 'type'
        :param bool stack_widget: stack this widget below the previous one.

        """
        kwargs['rows'] = kwargs.get('rows', 10)
        return ChartWidget.create(*args, charttype='column', **kwargs)


class LineWidget(ChartWidget):
    @classmethod
    def create(cls, *args, **kwargs):
        """Create a widget displaying data as a line chart.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 10)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: List of data columns to graph
        :param str charttype: Type of chart, defaults to 'line'.  This may be
           any YUI3 'type'
        :param bool stack_widget: stack this widget below the previous one.

        """
        kwargs['rows'] = kwargs.get('rows', 0)
        return ChartWidget.create(*args, charttype='line', **kwargs)


class CandleStickWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               keycols=None, valuecols=None, charttype='candlestick',
               stack_widget=False):
        """Create a widget displaying stock prices as a candle stick chart.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: List of data columns to graph
        :param str charttype: Type of chart, defaults to 'candlestick'.
        :param bool stack_widget: stack this widget below the previous one.

        The Y axis of this widget can't dynamically scale to different ranges.
        """
        w = Widget(section=section, title=title, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__,
                   stack_widget=stack_widget)
        w.compute_row_col()
        if keycols is None:
            keycols = [col.name for col in table.get_columns()
                       if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" %
                             str(table))

        if valuecols is None:
            valuecols = [col.name for col in table.get_columns()
                         if col.iskey is False]
        w.options = JsonDict(dict={'keycols': keycols,
                                   'columns': valuecols,
                                   'axes': None,
                                   'charttype': charttype})
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        price_names = ["open", "high", "low", "close"]

        w_axes = {"date_range": {"keys": ["date"],
                                 "position": "bottom",
                                 "type": "time",
                                 "styles": {"label": {"rotation": "-45",
                                            "fontSize": "8pt"},
                                            "majorUnit": {"count": 5}
                                            },
                                 },
                  "candle": {"keys": price_names,
                             "type": "numeric",
                             # YUI seems to always add a default axis
                             # (also can not change the scale)
                             # thus set position to be none for this axis
                             # it is required to render the candle stick graph
                             "position": "none"}
                  }

        seriesCollection = [{"type": "candlestick",
                             "xKey": 'date',
                             "yAxis": "candle"}]

        rows = [dict(zip(["date"] + price_names, day)) for day in data]
        ret = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": widget.options.charttype,
            "dataProvider": rows,
            "seriesCollection": seriesCollection,
            "axes": w_axes,
            "seriesKeys": [price_names],
            "interactionType": "planar",
        }
        return ret
