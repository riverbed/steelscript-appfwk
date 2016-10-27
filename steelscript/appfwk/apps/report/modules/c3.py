# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import re
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from steelscript.common.datastructures import JsonDict
from steelscript.appfwk.apps.report.models import Widget
from steelscript.common.timeutils import force_to_utc

logger = logging.getLogger(__name__)


def cleankey(s):
    return re.sub('[:. ]', '_', s)


class TimeSeriesWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               keycols=None, valuecols='*', altaxis=None, stacked=False):
        """Create a widget displaying data as a chart.

        This class is typically not used directly, but via LineWidget
        or BarWidget subclasses

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)
        :param list keycols: List of key column names to use for x-axis labels
        :param list valuecols: List of data columns to graph
        :param list altaxis: List of columns to graph using the
            alternate Y-axis
        :param str stacked: True if stacked chart, defaults to False.

        """
        w = Widget(section=section, title=title, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        if keycols is None:
            keycols = [col.name for col in table.get_columns()
                       if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" %
                             str(table))

        w.options = JsonDict(dict={'keycols': keycols,
                                   'columns': valuecols,
                                   'altaxis': altaxis,
                                   'stacked': stacked})
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, fmt):
                self.col = col
                self.dataindex = dataindex
                self.formatter = fmt

        all_cols = job.get_columns()

        # The category "key" column -- this is the column shown along the
        # bottom of the bar widget
        keycols = [c for c in all_cols if c.name in widget.options.keycols]
        catname = '-'.join([k.name for k in keycols])

        # columns of '*' is a special case, just use all
        # defined columns other than time
        if widget.options.columns == '*':
            cols = [c for c in all_cols if not c.iskey]
        else:
            # The value columns - one set of bars for each
            cols = [c for c in all_cols if c.name in widget.options.columns]

        if widget.options.altaxis:
            altcols = [c.name for c in all_cols if
                       c.name in widget.options.altaxis]
        else:
            altcols = []

        # Map of column info by column name
        colmap = {}

        # Build up the colmap
        for i, c in enumerate(all_cols):
            if c not in keycols and c not in cols:
                continue
            if c.isnumeric():
                if c.units == c.UNITS_PCT:
                    fmt = 'formatPct'
                else:
                    if c.datatype == c.DATATYPE_FLOAT:
                        fmt = 'formatMetric'
                    elif c.datatype == c.DATATYPE_INTEGER:
                        fmt = 'formatIntegerMetric'
            elif c.istime():
                fmt = 'formatTime'

            ci = ColInfo(c, i, fmt)
            colmap[c.name] = ci

        # Array of data.  First row is the column labels
        rows = [[c.col.name for c in colmap.values()]]

        t0 = None
        t1 = None

        def c3datefmt(d):
            return force_to_utc(d).strftime('%Y-%m-%d %H:%M:%S')

        for rawrow in data:
            row = []

            for c in colmap.values():
                v = rawrow[c.dataindex]
                if c.col.istime():
                    if not t0 or v < t0:
                        t0 = v
                    if not t1 or v > t1:
                        t1 = v
                    v = c3datefmt(v)

                row.append(v)

            rows.append(row)

        # chartdef = {
        #     data: {
        #         json: [ { k1: 1, v1: 2, v2: 'baz'},
        #                 { k1: 1, v1: 2, v2: 'baz'},
        #                 ... ],
        #         keys: { x: 'k1',
        #                 values: ['v1', 'v2'] },
        #         xFormat: '%Y-%m-%d'
        #     },
        #     axis: {
        #         x: {
        #             type: 'timeseries',
        #             localtime: true,
        #             tick: {
        #                 format: "%H:%M:%S",
        #                 values: ['2015-07-05 13:20:00', '2015-07-05 13:25:00',
        #                          '2015-07-05 13:30:00', '2015-07-05 13:35:00']
        #             }
        #         }
        #     }
        #
        timeaxis = TimeAxis([t0, t1])
        timeaxis.compute()
        tickvalues = [c3datefmt(d) for d in timeaxis.ticks]

        data = {
            'chartTitle': widget.title.format(**job.actual_criteria),
            'rows': rows,
            'names': {c.col.name: c.col.label for c in colmap.values()},
            'altaxis': {c: 'y2' for c in altcols} or None,
            'tickFormat': timeaxis.best[1],
            'tickValues': tickvalues,
            'type': 'line'
        }

        if widget.options.stacked:
            data['groups'] = [[c.col.label for c in colmap.values()
                               if not c.col.iskey]]
            data['type'] = 'area'

        return data


class TimeAxis(object):

    INTERVALS = [
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
         lambda(d): datetime(d.year, d.month, d.day, d.hour, d.minute - d.minute%10, tzinfo=d.tzinfo) + timedelta(minutes=5)],
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

        bsecs = best[0].total_seconds()
        multiple = int((secs / bsecs) / (maxticks - 1)) + 1

        t = best[2](t0)
        ticks = [t]
        while t < t1:
            t = t + best[0] * multiple
            ticks.append(t)

        self.ticks = ticks
        self.best = best
