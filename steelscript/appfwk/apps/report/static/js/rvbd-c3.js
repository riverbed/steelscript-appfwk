/**
 # Copyright (c) 2016 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the MIT License
 # accompanying the software ("License").  This software is distributed "AS IS"
 # as set forth in the License.
 */

(function() {
'use strict';

rvbd.widgets.c3 = {};

rvbd.widgets.c3.C3Widget = function(postUrl, isEmbedded, div,
                                    id, slug, options, criteria, dataCache) {
    var self = this;

    var ct = $(window);
    ct.resize(function() { self.onResize(); });

    rvbd.widgets.Widget.apply(self, [postUrl, isEmbedded, div,
                                     id, slug, options, criteria, dataCache]);
};

/* C3 Widget base class */
rvbd.widgets.c3.C3Widget.prototype = Object.create(rvbd.widgets.Widget.prototype);

$.extend(rvbd.widgets.c3.C3Widget.prototype, {

    /* Called when the widget is resized (or created) */
    onResize: function() {
        var self = this;
        self.render(self.data);
    },
    
    generateColor: function(color, d) {
	var column, hash = 0;
	if (rvbd.report.color_palette == 'default') {
	    return color; 
	} else if (typeof d === 'string') {
	    column = d;
	} else if (d.hasOwnProperty('id')) {
	    if (typeof d.id === 'string') {
		column = d.id;  
	    } else {
		return color; 
	    }
	} else {
	    return color;
	}
	
	var index = rvbd.report.columns.sort().indexOf(column);
	
	/* this recursivce method converts hash to index (any number from 0 to 20)
	   by summarizing all digits in hash */ 
	function sumDigits(number) {
	    var sum = Math.abs(number).toString()
		.split('')
		.map(Number)
		.reduce(function(a,b){
		    return +a + +b;
		}, 0);
	    
	    if (sum >= 10) {
		sum = sumDigits(sum);
	    }
	    
	    return sum; 
	}
	
	if (rvbd.report.color_palette == 'category10') {
	    if (index >= 10) {
		index = sumDigits(index);
	    }
	}
	
	return d3.scale[rvbd.report.color_palette]().domain(d3.range(0, index))(index);
    }
});
    
/**
 * TimeSeriesWidget -- does a generic bar chart
 *
 */

rvbd.widgets.c3.TimeSeriesWidget = function(postUrl, isEmbedded, div,
                                            id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.c3.C3Widget.apply(self, [postUrl, isEmbedded, div,
                                          id, slug, options, criteria, dataCache]);
};
rvbd.widgets.c3.TimeSeriesWidget.prototype =
        Object.create(rvbd.widgets.c3.C3Widget.prototype);

$.extend(rvbd.widgets.c3.TimeSeriesWidget.prototype, {
    render: function(data) {
        var self = this;
        self.data = data;
        if (typeof data['chartTitle'] !== "undefined") {
            self.titleMsg = data['chartTitle'];
        }
        self.buildInnerLayout();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight -
                      self.titleHeight);

        var chartdef = {
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                json: data.json,
                keys: {x: data.key,
                       value: data.values},
                names: data.names,
                type: data.type,
		color : function (color, d) {
		    return self.generateColor(color, d);
		},
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
                    value: function (value, ratio, id) { return d3.format(',')(Math.round(value)); }
                }
            }
        };

        if (data.altaxis) {
            chartdef.data.axes = data.altaxis;
            chartdef.axis.y2 = {
                show: true, 
		tick: {
		    format: function (d) { return d3.format('s')(Math.abs(d)); }
		}
            };
        }

        self.widget = c3.generate(chartdef);
    }
});

/**
 * PieWidget
 *
 */

rvbd.widgets.c3.PieWidget = function(postUrl, isEmbedded, div,
                                     id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.c3.C3Widget.apply(self, [postUrl, isEmbedded, div,
                                          id, slug, options, criteria, dataCache]);
};
rvbd.widgets.c3.PieWidget.prototype =
    Object.create(rvbd.widgets.c3.C3Widget.prototype);

$.extend(rvbd.widgets.c3.PieWidget.prototype, {
    render: function(data) {
        var self = this;
        self.data = data;

        if (typeof data['chartTitle'] !== "undefined") {
            self.titleMsg = data['chartTitle'];
        }
        self.buildInnerLayout();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight);

        var chartdef = {
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                columns: data.rows,
                type: data.type,
		color : function (color, d) {
		    return color;
		},
            },
            legend: {
                position: 'inset'
            },
        };

        self.widget = c3.generate(chartdef);
    }
});


/**
 * ChartWidget - can be either bar or line widget types
 *
 */

rvbd.widgets.c3.ChartWidget = function(postUrl, isEmbedded, div,
                                       id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.c3.C3Widget.apply(self, [postUrl, isEmbedded, div,
                                          id, slug, options, criteria, dataCache]);
};
rvbd.widgets.c3.ChartWidget.prototype =
    Object.create(rvbd.widgets.c3.C3Widget.prototype);

$.extend(rvbd.widgets.c3.ChartWidget.prototype, {
    render: function(data) {
        var self = this;
        self.data = data;

        if (typeof data['chartTitle'] !== "undefined") {
            self.titleMsg = data['chartTitle'];
        }
        self.buildInnerLayout();

        var height = ($(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight);

        var chartdef = {
            bindto: '#' + $(self.content).attr('id'),
            size: {
                height: height
            },
            data: {
                json: data.rows,
                type: data.type,
                names: data.names,
                keys: {
                    x: data.keyname,
                    value: data.values
                },
		color : function (color, d) {
		    return self.generateColor(color, d);
		}
            },
            legend: {
                position: 'inset',
                inset: {
                    anchor: 'top-right',
                    x: 20,
                    y: 10
                }
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

        self.widget = c3.generate(chartdef);
    }
});

})();
