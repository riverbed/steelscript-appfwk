# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


"""
This module provides base mapping classes for specific APIs to leverage
"""

import os.path
import logging
import threading
from collections import namedtuple

import pygeoip
from pygeoip.util import ip2long
from django.core.exceptions import ObjectDoesNotExist

from steelscript.common.datastructures import JsonDict
from steelscript.appfwk.apps.report.models import Widget
from steelscript.appfwk.apps.preferences.models import SystemSettings
from steelscript.appfwk.apps.geolocation.models import Location
from steelscript.appfwk.apps.geolocation.geoip import LookupIP
from .maps_providers import google_postprocess, openstreetmaps_postprocess


logger = logging.getLogger(__name__)

POST_PROCESS_MAP = {'DISABLED': google_postprocess,
                    'DEVELOPER': google_postprocess,
                    'FREE': google_postprocess,
                    'BUSINESS': google_postprocess,
                    'OPEN_STREET_MAPS': openstreetmaps_postprocess,
                    'STATIC_MAPS': lambda x: x,
                    }


def authorized():
    """ Verifies the Maps API can be used given the version selected
        and the API key supplied.

        Returns True/False, and an error message if applicable
    """
    settings = SystemSettings.get_system_settings()

    if settings.maps_version == 'DISABLED':
        msg = (u'Maps API has been disabled.\n'
               'See Admin User for changes.')
        return False, msg
    elif (settings.maps_version in ('FREE', 'BUSINESS') and
          not settings.maps_api_key):
        msg = (u'A valid API_KEY must be provided for either \n'
               '"Free" or "Business" Google Maps API choices.\n'
               'See Configure->Preferences to update.')
        return False, msg
    else:
        return True, ''


class MapWidgetOptions(JsonDict):
    _default = {'key': None,
                'latitude': None,
                'longitude': None,
                'label': None,
                'value': None,
                'min_bounds': None,
                'url': None}
    _required = ['value']


class MapWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               lat_col=None, long_col=None, val_col=None, label_col=None,
               url_col=None, min_bounds=None):
        """Create a widget displaying data overlayed on a map.

        :param int width: Width of the widget in columns (1-12, default 6)
        :param int height: Height of the widget in pixels (default 300)

        :param float lat_col, long_col: are optional pairs of columns
            indicating the latitude and longitude values of data to
            plot.  If these are omitted, the first column with the
            attribute 'iskey' will be used as the means for
            determining where to plot.

        :param str/col val_col: the data column to graph, defaults to
            the first non-key column found assigned to the table.

        :param str/col label_col: column to use for marker labels
            when when defining lat/long columns.

        :param str url_col: column to use for URL to redirect to when marker
            gets cliecked.

        :param tuple min_bounds: tuple of (lat, lng) points
            representing the minimum extents that the map should
            include.  Useful to avoid the close zoomed-in effect when
            two close-in points would be plotted.  For example, to
            have continental US always shown, the argument could be:
            ``((33.184833, -116.999540), (45.561302, -67.956573))``

        Each column argument may be a Column object or the string name.

        """
        w = Widget(section=section, title=title, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()

        if lat_col is None and long_col is None:
            keycol = [col.name for col in table.get_columns()
                      if col.iskey is True]
            if len(keycol) == 0:
                raise ValueError("Table %s does not have any key columns "
                                 "defined" % str(table))
            elif len(keycol) > 1:
                logger.debug('Widget %s: Choosing first key column from '
                             'available list %s ' % (repr(w), keycol))
            keycol = keycol[0]
        elif lat_col and long_col:
            keycol = None
            lat_col = getattr(lat_col, 'name', lat_col)
            long_col = getattr(long_col, 'name', long_col)
            label_col = getattr(label_col, 'label', label_col)
        else:
            raise ValueError('Both lat_col and long_col need to be defined '
                             'as a pair or omitted as a pair.')

        if val_col:
            val_col = getattr(val_col, 'name', val_col)
        else:
            val_col = [col.name for col in table.get_columns() if
                       col.iskey is False][0]

        w.options = MapWidgetOptions(key=keycol, latitude=lat_col,
                                     longitude=long_col, value=val_col,
                                     label=label_col, url=url_col,
                                     min_bounds=min_bounds)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        """Class method to generate list of circle objects.

        Subclass should manipulate this list into specific
        JSON structures as needed.
        """

        settings = SystemSettings.get_system_settings()
        maps_version = settings.maps_version
        post_process = POST_PROCESS_MAP[maps_version]

        columns = job.get_columns()

        ColInfo = namedtuple('ColInfo', ['col', 'dataindex'])

        keycol = None
        latcol = None
        longcol = None
        valuecol = None
        labelcol = None
        urlcol = None
        for i, c in enumerate(columns):
            if c.name == widget.options.key:
                keycol = ColInfo(c, i)
            elif c.name == widget.options.latitude:
                latcol = ColInfo(c, i)
            elif c.name == widget.options.longitude:
                longcol = ColInfo(c, i)
            elif c.name == widget.options.value:
                valuecol = ColInfo(c, i)
            elif c.name == widget.options.label:
                labelcol = ColInfo(c, i)
            elif c.name == widget.options.url:
                urlcol = ColInfo(c, i)

        # Array of circle objects for each data row
        Circle = namedtuple('Circle',
                            ['title', 'lat', 'long', 'value', 'size', 'url',
                             'units', 'formatter'])
        circles = []

        if data:
            valmin = None
            valmax = None
            if valuecol.col.isnumeric():
                values = zip(*data)[valuecol.dataindex]
                filtered = filter(bool, values)
                if filtered:
                    valmin = min(filtered)
                    valmax = max(filtered)
                else:
                    valmin = 1
                    valmax = 1

            geolookup = None

            if valuecol.col.isnumeric():
                formatter = 'formatMetric'
            else:
                formatter = None

            for rawrow in data:
                val = rawrow[valuecol.dataindex]

                # skip empty result values which are not explicitly zero
                if val is None or val == '':
                    continue

                if valmax:
                    normalized = float(val - valmin) / float(valmax - valmin)
                    marker_size = 5 + normalized * 20
                else:
                    marker_size = 5

                if keycol:
                    key = rawrow[keycol.dataindex]

                    # XXXCJ - this is a hack for NetProfiler based host groups,
                    # need to generalize this, probably via options
                    if widget.table().options.get('groupby') == 'host_group':
                        try:
                            geo = Location.objects.get(name=key)
                        except ObjectDoesNotExist:
                            continue
                    else:
                        # Perform geolookup on the key
                        # (should be an IP address...)
                        if geolookup is None:
                            geolookup = LookupIP.instance()
                        geo = geolookup.lookup(key)

                    if geo:
                        # Found a match, create a Circle
                        url = rawrow[urlcol.dataindex] if urlcol else None

                        circle = Circle(title=geo.name,
                                        lat=geo.latitude,
                                        long=geo.longitude,
                                        value=val,
                                        size=marker_size,
                                        units=valuecol.col.units_str(),
                                        formatter=formatter,
                                        url=url)
                        circles.append(circle)
                else:
                    # use lat/long columns instead of lookups
                    lat = rawrow[latcol.dataindex]
                    long = rawrow[longcol.dataindex]
                    title = rawrow[labelcol.dataindex] if labelcol else val
                    url = rawrow[urlcol.dataindex] if urlcol else None

                    circle = Circle(title=title,
                                    lat=lat,
                                    long=long,
                                    value=val,
                                    size=marker_size,
                                    units=valuecol.col.units_str(),
                                    formatter=formatter,
                                    url=url)
                    circles.append(circle)

        else:
            # no data just return empty circles list
            pass

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "circles": circles,
            "minbounds": widget.options.min_bounds
        }

        return post_process(data)


class subnet(object):
    def __init__(self, addr, mask, lat, lng, name):
        self.addr = ip2long(addr)
        self.mask = ip2long(mask)
        self.lat = lat
        self.long = lng
        self.name = name

    def match(self, a):
        return (ip2long(a) & self.mask) == self.addr
