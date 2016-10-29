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

        self.titleMsg = data['chartTitle'];
        self.buildInnerLayout();

        var $content = $(self.content);
        self.contentExtraWidth  = parseInt($content.css('margin-left'), 10) +
                                  parseInt($content.css('margin-right'), 10);
        self.contentExtraHeight = parseInt($content.css('margin-top'), 10) +
                                  parseInt($content.css('margin-bottom'), 10);
        self.titleHeight = $(self.title).outerHeight();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight -
                      self.titleHeight);

        var chartdef = {
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                //rows: data.rows,
                json: data.json,
                keys: {x: data.key,
                       value: data.values},
                names: data.names,
                type: data.type,
                x: 'time',
                // "2016-10-28T18:49:24.000Z"
                xFormat: '%Y-%m-%dT%H:%M:%S.%LZ',
                xLocaltime: false
            },
            legend: {
                position: 'inset'
            },
            point: {
                r: 2
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
                    title: function (x) { return d3.time.format('%Y-%m-%d ' + data.tickFormat)(x); },
                    value: function (value, ratio, id) { return d3.format('.3s')(value); }
                }
            }
        };

        if (data.altaxis) {
            chartdef.data.axes = data.altaxis;
            chartdef.axis.y2 = {
                show: true
            };
        }

        c3.generate(chartdef);

    }
});

/**
 * PieWidget
 *
 */

rvbd.widgets.c3.PieWidget = function(postUrl, isEmbedded, div,
                                            id, slug, options, criteria) {
    var self = this;

    rvbd.widgets.c3.C3Widget.apply(self, [postUrl, isEmbedded, div,
        id, slug, options, criteria]);
};
rvbd.widgets.c3.PieWidget.prototype =
    Object.create(rvbd.widgets.c3.C3Widget.prototype);

$.extend(rvbd.widgets.c3.PieWidget.prototype, {
    render: function(data) {
        var self = this;
        self.data = data;

        self.titleMsg = data['chartTitle'];
        self.buildInnerLayout();

        var $content = $(self.content);
        self.contentExtraWidth  = parseInt($content.css('margin-left'), 10) +
            parseInt($content.css('margin-right'), 10);
        self.contentExtraHeight = parseInt($content.css('margin-top'), 10) +
            parseInt($content.css('margin-bottom'), 10);
        self.titleHeight = $(self.title).outerHeight();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight);

        var chartdef = {
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                columns: data.rows,
                //names: data.names,
                type: data.type,
                //groups: data.groups,
                //x: 'time',
                //xFormat: '%Y-%m-%d %H:%M:%S',
                //xLocaltime: false
            },
            legend: {
                position: 'inset'
            },
        };

        c3.generate(chartdef);

    }
});


/**
 * ChartWidget - can be either bar or line widget types
 *
 */

rvbd.widgets.c3.ChartWidget = function(postUrl, isEmbedded, div,
                                            id, slug, options, criteria) {
    var self = this;

    rvbd.widgets.c3.C3Widget.apply(self, [postUrl, isEmbedded, div,
        id, slug, options, criteria]);
};
rvbd.widgets.c3.ChartWidget.prototype =
    Object.create(rvbd.widgets.c3.C3Widget.prototype);

$.extend(rvbd.widgets.c3.ChartWidget.prototype, {
    render: function(data) {
        var self = this;
        self.data = data;

        self.titleMsg = data['chartTitle'];
        self.buildInnerLayout();

        var $content = $(self.content);
        self.contentExtraWidth  = parseInt($content.css('margin-left'), 10) +
            parseInt($content.css('margin-right'), 10);
        self.contentExtraHeight = parseInt($content.css('margin-top'), 10) +
            parseInt($content.css('margin-bottom'), 10);
        self.titleHeight = $(self.title).outerHeight();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight);

        var chartdef = {
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                json: data.rows,
                type: data.type,
                keys: {
                    x: data.keyname,
                    value: data.values
                }
            },
            legend: {
                position: 'inset'
            },
            axis: {
                x: {
                    type: 'category',
                    // negative rotated text doesn't automatically resize yet
                    // https://github.com/c3js/c3/issues/1511
                    //tick: {
                    //    rotate: -60
                    //}
                }
            }
        };

        if (data.type == 'bar') {
            chartdef.bar = {
                width: {
                    ratio: 0.5
                }
            }
        }

        c3.generate(chartdef);

    }
});

})();
