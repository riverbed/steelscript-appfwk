/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

(function() {
'use strict';

rvbd.widgets.c3 = {};

rvbd.widgets.c3.C3Widget = function(postUrl, isEmbedded, div,
                                    id, slug, options, criteria) {
    var self = this;

    var ct = $(window);
    ct.resize(function() { self.onResize(); });

    rvbd.widgets.Widget.apply(self, [postUrl, isEmbedded, div,
                                     id, slug, options, criteria]);
};

/* C3 Widget base class */
rvbd.widgets.c3.C3Widget.prototype = Object.create(rvbd.widgets.Widget.prototype);

$.extend(rvbd.widgets.c3.C3Widget.prototype, {

    /* Called when the YUI widget is resized (or created) */
    onResize: function() {
        var self = this;
        self.render(self.data);
    },

});

/**
 * TimeSeriesWidget -- does a generic bar chart
 *
 */

rvbd.widgets.c3.TimeSeriesWidget = function(postUrl, isEmbedded, div,
                                       id, slug, options, criteria) {
    var self = this;

    rvbd.widgets.c3.C3Widget.apply(self, [postUrl, isEmbedded, div,
                                          id, slug, options, criteria]);
};
rvbd.widgets.c3.TimeSeriesWidget.prototype =
        Object.create(rvbd.widgets.c3.C3Widget.prototype);

$.extend(rvbd.widgets.c3.TimeSeriesWidget.prototype, {
    render: function(data) {
        var self = this;
        self.data = data;
        var chartdef = data.chartDef;

        self.titleMsg = data['chartTitle'];
        self.buildInnerLayout();

        var $content = $(self.content)
        self.contentExtraWidth  = parseInt($content.css('margin-left'), 10) +
                                  parseInt($content.css('margin-right'), 10);
        self.contentExtraHeight = parseInt($content.css('margin-top'), 10) +
                                  parseInt($content.css('margin-bottom'), 10);
        self.titleHeight = $(self.title).outerHeight();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight -
                      self.titleHeight);

        var content = c3.generate({
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                rows: data.rows,
                type: data.type,
                groups: data.groups,
                x: 'Time',
                xFormat: '%Y-%m-%d %H:%M:%S',
                xLocaltime: false
            },
            legend: {
                position: 'inset'
            },
            point: {
                r: 1
            },
            axis: {
                x: {
                    type: 'timeseries',
                    tick: {
                        format: data.tickFormat,
                        values: data.tickValues
                    }
                },
                y: {
                    tick: {
                        format: function (d) { return d3.format('s')(Math.abs(d)); }
                    }
                }
            },
            tooltip: {
                format: {
                    title: function (x) { return d3.time.format('%Y-%m-%d %H:%M:%S')(x); },
                    value: function (value, ratio, id) { return d3.format('.3s')(value); }
                }
            }
        });

    }
});

})();
