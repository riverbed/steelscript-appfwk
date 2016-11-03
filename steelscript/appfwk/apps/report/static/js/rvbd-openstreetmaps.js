/**
 # Copyright (c) 2016 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the MIT License
 # accompanying the software ("License").  This software is distributed "AS IS"
 # as set forth in the License.
 */

rvbd.widgets.maps = {};

rvbd.widgets.maps.MapWidget = function (postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    rvbd.widgets.Widget.apply(this, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.maps.MapWidget.prototype = Object.create(rvbd.widgets.Widget.prototype)

rvbd.widgets.maps.MapWidget.prototype.render = function(data)
{
    var self = this;

    var $div = $(self.div);

 // Ignore options here due to bug:
 // https://github.com/Leaflet/Leaflet/issues/2071
    var mapOptions = {
 //       center: [42.3583, -71.063],
 //       zoom: 3,
    };

    self.titleMsg = data['chartTitle'];
    self.buildInnerLayout();

    $(self.content)
        .height($div.height() - 52);


    var map = new L.map(self.content, mapOptions);

    L.tileLayer('http://{s}.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg', {
        subdomains: ['otile1', 'otile2', 'otile3', 'otile4'],
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png">',
    }).addTo(map);

    // If we have the weather layer enabled
    if (rvbd.report.weatherWidget.enabled) {
        // Add a URL parameter which will invalidate the image cache every 15 minutes
        rvbd.report.weatherWidget.url = appendCurrentTimeUrlParam(rvbd.report.weatherWidget.url, rvbd.report.weatherWidget.timeout);
        // Then add our layer to the map
        L.tileLayer(rvbd.report.weatherWidget.url).addTo(map);
    }


    if (data.minbounds) {
        bounds = new L.LatLngBounds(
            data.minbounds[0],
            data.minbounds[1]
        );
    } else {
        bounds = new L.LatLngBounds();
    }

    var valStr, title, marker;
    $.each(data.circles, function(i,c) {
        c.center = [c.center[0], c.center[1]];
        bounds.extend(c.center)

        valStr = (c.formatter ? rvbd.formatters[c.formatter](c.value, 2)
                              : c.value);
        if (c.units) {
            valStr = valStr + ' ' + c.units;
        }

        title = c.title + '\n' + valStr;

        marker = L.marker(c.center, {
            title: title,
            icon: L.divIcon({
                className: 'circleMarker',
                iconSize: [c.radius * 2, c.radius * 2]
            })
        }).addTo(map);
    });
    bounds = bounds.pad(0.10);
    map.fitBounds(bounds);
}

