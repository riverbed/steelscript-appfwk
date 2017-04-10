# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import json
import logging
from datetime import datetime, timedelta

import pandas
from dateutil.relativedelta import relativedelta

from steelscript.appfwk.apps.report.models import Widget, UIWidgetHelper
from steelscript.common.timeutils import force_to_utc

logger = logging.getLogger(__name__)


class BaseWidget(object):
    @classmethod
    def calculate_keycol(cls, table, keycols):
        if keycols is None:
            keycols = [col.name for col in table.get_columns()
                       if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" %
                             str(table))
        return keycols


class TimeSeriesWidget(BaseWidget):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               keycols=None, valuecols=None, altaxis=None, bar=False,
               stacked=False, stack_widget=False):
        """Create a widget displaying data as a chart.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: List of data columns to graph
        :param list altaxis: List of columns to graph using the
            alternate Y-axis
        :param bool bar: If True, show time series in a bar chart.  Can
          be combined with ``stacked`` to show as stacked bar chart rather
          than stacked area chart
        :param str stacked: True for stacked line chart, defaults to False
        :param bool stack_widget: stack this widget below the previous one

        """
        keycols = cls.calculate_keycol(table, keycols)

        options = {'keycols': keycols,
                   'columns': valuecols,
                   'altaxis': altaxis,
                   'bar': bar,
                   'stacked': stacked}

        Widget.create(section=section, table=table, title=title,
                      width=width, rows=-1, height=height,
                      module=__name__, uiwidget=cls.__name__,
                      options=options, stack_widget=stack_widget)

    @classmethod
    def process(cls, widget, job, data):
        helper = UIWidgetHelper(widget, job)

        catname = '-'.join([k.name for k in helper.keycols])
        timecol = [c for c in helper.keycols if c.istime() or c.isdate()][0]

        if widget.options.altaxis:
            altcols = [c.name for c in helper.all_cols if
                       c.name in widget.options.altaxis]
        else:
            altcols = []

        def c3datefmt(d):
            return '%s.%s' % (force_to_utc(d).strftime('%Y-%m-%dT%H:%M:%S'),
                              "%03dZ" % int(d.microsecond / 1000))

        df = pandas.DataFrame(data, columns=helper.col_names)
        t0 = df[timecol.name].min()
        t1 = df[timecol.name].max()

        timeaxis = TimeAxis([t0, t1])
        timeaxis.compute()

        tickvalues = [c3datefmt(d) for d in timeaxis.ticks]

        rows = json.loads(
            df.to_json(orient='records', date_format='iso', date_unit='ms')
        )

        data = {
            'chartTitle': widget.title.format(**job.actual_criteria),
            'json': rows,
            'key': catname,
            'values': [c.name for c in helper.valcols],
            'names': {c.col.name: c.col.label for c in helper.colmap.values()},
            'altaxis': {c: 'y2' for c in altcols} or None,
            'tickFormat': timeaxis.best[1],
            'tickValues': tickvalues,
            'type': 'line'
        }

        if widget.options.stacked:
            data['groups'] = [[c.col.label for c in helper.colmap.values()
                               if not c.col.iskey]]
            data['type'] = 'area'

        if widget.options.bar:
            # can override 'area' type, or just be used as a plain bar display
            data['type'] = 'bar'

        return data


class PieWidget(BaseWidget):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300,
               stack_widget=False):
        """Create a widget displaying data in a pie chart.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display as pie slices (default 10)
        :param bool stack_widget: stack this widget below the previous one.

        The labels are taken from the Table key column (the first key,
        if the table has multiple key columns defined).  The pie
        widget values are taken from the sort column.

        """
        keycols = cls.calculate_keycol(table, keycols=None)

        if table.sortcols is None:
            raise ValueError("Table %s does not have a sort column defined" %
                             str(table))

        options = {'key': keycols[0],
                   'value': table.sortcols[0]}

        Widget.create(section=section, table=table, title=title,
                      width=width, rows=rows, height=height,
                      module=__name__, uiwidget=cls.__name__,
                      options=options, stack_widget=stack_widget)

    @classmethod
    def process(cls, widget, job, data):
        columns = job.get_columns()

        col_names = [c.name for c in columns]

        catcol = [c for c in columns if c.name == widget.options.key][0]
        col = [c for c in columns if c.name == widget.options.value][0]

        # For each slice, catcol will be the label, col will be the value
        rows = []

        if data:
            for rawrow in data:
                row = dict(zip(col_names, rawrow))
                r = [row[catcol.name], row[col.name]]
                rows.append(r)
        else:
            # create a "full" pie to show something
            rows = [[1, 1]]

        data = {
            'chartTitle': widget.title.format(**job.actual_criteria),
            'rows': rows,
            'type': 'pie',
        }

        return data


class ChartWidget(BaseWidget):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300,
               keycols=None, valuecols=None, charttype='line',
               **kwargs):
        """Create a widget displaying data as a chart.

        This class is typically not used directly, but via LineWidget
        or BarWidget subclasses

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param int rows: Number of rows to display (default 10)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: Optional list of data columns to graph
        :param str charttype: Type of chart, defaults to 'line'.  This may be
           any C3 'type'

        """
        keycols = cls.calculate_keycol(table, keycols=None)

        if table.sortcols is None:
            raise ValueError("Table %s does not have a sort column defined" %
                             str(table))

        if valuecols is None:
            valuecols = [col.name for col in table.get_columns()
                         if col.iskey is False]

        options = {'keycols': keycols,
                   'columns': valuecols,
                   'charttype': charttype}

        Widget.create(section=section, table=table, title=title,
                      width=width, rows=rows, height=height,
                      module=__name__, uiwidget=cls.__name__,
                      options=options, **kwargs)

    @classmethod
    def process(cls, widget, job, data):
        helper = UIWidgetHelper(widget, job)

        # create composite name for key label
        keyname = '-'.join([k.name for k in helper.keycols])

        # For each slice, keyname will be the label
        rows = []

        for rawrow in data:
            row = dict(zip([c.name for c in helper.all_cols], rawrow))

            # populate values first
            r = {c.name: row[c.name] for c in helper.valcols}

            # now add the key
            key = '-'.join([row[k.name] for k in helper.keycols])
            r[keyname] = key

            rows.append(r)

        data = {
            'chartTitle': widget.title.format(**job.actual_criteria),
            'rows': rows,
            'keyname': keyname,
            'values': [c.name for c in helper.valcols],
            'names': {c.col.name: c.col.label for c in helper.colmap.values()},
            'type': widget.options.charttype,
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
           any C3 'type'
        :param bool stack_widget: stack this widget below the previous one.

        """
        kwargs['rows'] = kwargs.get('rows', 10)
        return ChartWidget.create(*args, charttype='bar', **kwargs)


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
           any C3 'type'
        :param bool stack_widget: stack this widget below the previous one.

        """
        kwargs['rows'] = kwargs.get('rows', 0)
        return ChartWidget.create(*args, charttype='line', **kwargs)


class TimeAxis(object):
    """Make reasonable ticks for arbitrary time intervals.

    For various sets of start and end times, this class will try to determine
    appropriate values to display on an X-Axis.

    The INTERVALS list contains
    a timedelta, format string, then two lambda functions to evaluate a length
    of time.  The class gets initialized with two times - t0 and t1 plus some
    optional limits on how many ticks to solve for.

    When calculating the ticks, each item in INTERVALS gets evaluated against
    t0/t1 until an appropriate time range gets found then reasonable multiples
    are determined within that boundary and returned.

    """

    INTERVALS = [
        [timedelta(milliseconds=1), '%H:%M:%S.%L',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute, d.second, d.microsecond, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute, d.second, d.microsecond, tzinfo=d.tzinfo) + timedelta(milliseconds=1)],
        [timedelta(seconds=1), '%H:%M:%S',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute, d.second, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute, d.second, tzinfo=d.tzinfo) + timedelta(seconds=1)],
        [timedelta(minutes=1), '%H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute, tzinfo=d.tzinfo) + timedelta(minutes=1)],
        [timedelta(minutes=5), '%H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%5, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%5, tzinfo=d.tzinfo) + timedelta(minutes=5)],
        [timedelta(minutes=10), '%H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%10, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%10, tzinfo=d.tzinfo) + timedelta(minutes=10)],
        [timedelta(minutes=15), '%H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%15, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%15, tzinfo=d.tzinfo) + timedelta(minutes=15)],
        [timedelta(minutes=30), '%H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%30, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%30, tzinfo=d.tzinfo) + timedelta(minutes=30)],
        [timedelta(hours=1), '%H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour, tzinfo=d.tzinfo) + timedelta(hours=1)],
        [timedelta(hours=12), '%b %d %Y %H:%M',
         lambda(d): datetime(d.year, d.month, d.day, d.hour - d.hour%12, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, d.hour - d.hour%12, tzinfo=d.tzinfo) + timedelta(hours=12)],
        [timedelta(days=1), '%b %d %Y',
         lambda(d): datetime(d.year, d.month, d.day, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day, tzinfo=d.tzinfo) + timedelta(days=1)],
        [timedelta(days=7), '%b %d %Y',
         lambda(d): datetime(d.year, d.month, d.day - d.weekday(), tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, d.day - d.weekday(), tzinfo=d.tzinfo) + timedelta(days=7)],
        [timedelta(days=30), '%b %Y',
         lambda(d): datetime(d.year, d.month, 1, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year, d.month, 1, tzinfo=d.tzinfo) + relativedelta(months=1)],
        [timedelta(days=365), '%Y',
         lambda(d): datetime(d.year, 1, 1, tzinfo=d.tzinfo),
         lambda(d): datetime(d.year+1, 1, 1, tzinfo=d.tzinfo)],
    ]

    def __init__(self, ts, minticks=5, maxticks=10):
        self.t0 = min(ts)
        self.t1 = max(ts)

        self.minticks = minticks
        self.maxticks = maxticks

        self.ticks = []

    def compute(self):
        t0 = self.t0
        t1 = self.t1
        minticks = self.minticks
        maxticks = self.maxticks

        # include_date = (t1.day != t0.day)

        secs = (t1-t0).total_seconds()

        best = None
        for i in self.INTERVALS:
            isecs = i[0].total_seconds()

            if (secs / isecs) < minticks:
                break

            best = i

        if best:
            bsecs = best[0].total_seconds()
            multiple = int((secs / bsecs) / (maxticks - 1)) + 1
        else:
            best = self.INTERVALS[0]
            multiple = 1

        t = best[2](t0)
        ticks = [t]
        while t < t1:
            t = t + best[0] * multiple
            ticks.append(t)

        self.ticks = ticks
        self.best = best
