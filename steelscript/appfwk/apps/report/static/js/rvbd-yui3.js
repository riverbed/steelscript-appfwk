/**
 # Copyright (c) 2016 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the MIT License
 # accompanying the software ("License").  This software is distributed "AS IS"
 # as set forth in the License.
 */

(function() {
'use strict';

rvbd.widgets.yui3 = {};

rvbd.widgets.yui3.YUIWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.Widget.apply(self, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.yui3.YUIWidget.prototype = Object.create(rvbd.widgets.Widget.prototype);

$.extend(rvbd.widgets.yui3.YUIWidget.prototype, {
    addBasicParams: function(data) {
        var self = this;

        var $div = $(self.div);

        data.render = '#' + $(self.content).attr('id');

        var width = $(self.outerContainer).width() - self.contentExtraWidth,
            height = $(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight;

        // Charts expect an integer width/height, tables expect a CSS-compatible width/height
        if (self.widgetClass === 'Chart') {
            data.width = width;
            data.height = height;
        } else {
            data.width = String(width) + 'px';
            data.height = String(height) + 'px';
        }

        return data;
    },

    /**
     * Implement in children to customize the config dictionary that will be passed to the YUI widget
     * constructor.
     */
    prepareData: function(data) {
        return data;
    },

    /* Called when the YUI widget is resized (or created) */
    onResize: function() {
        var self = this;

        // YUI widgets don't resize their content automatically when the size of their DIV changes.
        // For most (all?) widgets, we can just manually re-set their size and they'll automatically
        // re-render. (Resizing with JS also makes it easy to make the content DIV fill up all of the
        // remainining space after the title bar, which is tricky with pure CSS.)

        var width = $(self.outerContainer).width() - self.contentExtraWidth,
            height = $(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight;

        // Chart widgets take an integer pixels for dimensions, others take CSS dimensions
        if (self.widgetClass === 'Chart') {
            self.yuiWidget.set('width', width);
            self.yuiWidget.set('height', height);
        } else {
            self.yuiWidget.set('width', String(width) + 'px');
            self.yuiWidget.set('height', String(height) + 'px');
        }
    },

    /* Called immediately after onResize after the YUI widget is created. */
    onRender: function() {
        // Behavior implemented in subclasses
    },

    render: function(data) {
        var self = this;

        $(self.div).addClass('yui3-skin-sam');

        self.titleMsg = data['chartTitle'];
        self.buildInnerLayout();

        data = self.addBasicParams(data);
        data = self.prepareData(data);
        self.data = data;

        var requirements = self.requirements.concat(['event-resize']); // All widgets need event-resize

        // clean up the widget so it can be gc'd
        if (self.yuiWidget) {
            self.yuiWidget.destroy(true);
        }

        // only allocate one YUI instance and re-use it for follow on calls
        if (self.yuiHandle) {
            self.yuiWidget = new self.yuiHandle[self.widgetClass](data);
        } else {
            self.yuiHandle = YUI().use(requirements, function (Y) {
                self.yuiWidget = new Y[self.widgetClass](data);
                Y.on('windowresize', self.onResize.bind(self));
            });
        }
        self.onRender();
    }
});


rvbd.widgets.yui3.TableWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.yui3.YUIWidget.apply(self, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.yui3.TableWidget.prototype = Object.create(rvbd.widgets.yui3.YUIWidget.prototype);

$.extend(rvbd.widgets.yui3.TableWidget.prototype, {
    requirements: ['datatable-scroll', 'datatable-sort'],
    widgetClass: 'DataTable',

    prepareData: function(data) {
        data.scrollable = 'xy';

        $.each(data.columns, function(i, c) {
            var formatter;
            if (typeof c.formatter !== 'undefined') {
                if (c.formatter in rvbd.formatters) {
                    formatter = rvbd.formatters[c.formatter];
                } else {
                    formatter = eval(c.formatter);
                }
                c.formatter = (function(key, formatter) {
                    return function(v) { return formatter(v.data[key]); }
                })(c.key, formatter);
            }
        });

        return data;
    },

    isOversized: function() {
        var self = this;

        var $scroller = $(self.div).find('.yui3-datatable-y-scroller');

        // Return false if scroller is missing (i.e. widget failed to load properly)
        return $scroller.length === 0 || $scroller[0].scrollHeight > $scroller[0].clientHeight;
    },

    onRender: function() {
        var self = this;

        if (rvbd.report.expandTables && self.isOversized()) {
            // Table is oversized--expand widget to fit content
            var scroller = $(self.div).find('.yui3-datatable-y-scroller')[0];
            self.yuiWidget.set('height', (scroller.scrollHeight + 2) + 'px');
            $(this.div).css('height', 'auto');
        }
    }
});


rvbd.widgets.yui3.TimeSeriesWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.yui3.YUIWidget.apply(self, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.yui3.TimeSeriesWidget.prototype = Object.create(rvbd.widgets.yui3.YUIWidget.prototype);

$.extend(rvbd.widgets.yui3.TimeSeriesWidget.prototype, {
    requirements: ['charts-legend'],
    widgetClass: 'Chart',

    prepareData: function(data) {
        var self = this;

        $.each(data.axes, function(i, axis) {
            if ('formatter' in axis) { // A label formatting func is provided
                axis.labelFunction = (function(formatter) {
                    return function (v, fmt, tooltip) {
                        return formatter(v, tooltip ? 2 : 1);
                    }
                })(rvbd.formatters[axis.formatter]);
            } else if ('tickExponent' in axis && axis.tickExponent < 0) {
                axis.labelFunction = (function (exp) {
                    return function(v, fmt, tooltip) {
                        return tooltip ? v.toFixed(3 - exp) : v.toFixed(1 - exp);
                    }
                })(axis.tickExponent);
            }
        });

        data.tooltip = {};
        data.tooltip.setTextFunction = function(textField, val) {
            textField.setHTML(val);
            // the following will pick up all tooltips in page
            //var tt = $('.yui3-chart-tooltip');

            // instead, we find the one associated with the current field
            // then get its width and set the margin accordingly
            var width = $('#' + textField["_node"].id).width();
            textField.setStyle('margin-left', '-' + width + 'px');
        };

        data.tooltip.markerLabelFunction = function(cat, val, idx, s, sidx) {
            var msg =
                cat.displayName + ": " +
                cat.axis.get("labelFunction").apply(self, [cat.value, cat.axis.get("labelFormat"), true]) + "<br>" +
                val.displayName + ": " +
                val.axis.get("labelFunction").apply(self, [val.value, val.axis.get("labelFormat"), true]);

            return msg;
        };

        return data;
    }
});

rvbd.widgets.yui3.ChartWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.yui3.YUIWidget.apply(self, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.yui3.ChartWidget.prototype = Object.create(rvbd.widgets.yui3.YUIWidget.prototype);

$.extend(rvbd.widgets.yui3.ChartWidget.prototype, {
    requirements: ['charts-legend'],
    widgetClass: 'Chart',

    prepareData: function(data) {
        var n, axis;
        $.each([0, 1], function (i, v) {
            n = 'axis' + v;
            if (n in data.axes && data.axes[n].tickExponent < 0) {
                axis = data.axes[n];
                axis.labelFunction = (function (exp) {
                    return function(v, fmt, tooltip) {
                        return tooltip ? v.toFixed(3 - exp) : v.toFixed(1 - exp);
                    };
                })(axis.tickExponent);
            }
        });

        data.tooltip = {
            setTextFunction: function(textField, val) {
                textField.setHTML(val);
            },

            markerLabelFunction: function(cat, val, idx, s, sidx) {
                var msg =
                    cat.displayName + ": " +
                    cat.axis.get("labelFunction").apply(this, [cat.value, cat.axis.get("labelFormat"), true]) + "<br>" +
                    val.displayName + ": " +
                    val.axis.get("labelFunction").apply(this, [val.value, val.axis.get("labelFormat"), true]);

                return msg;
            }
        };

        return data;
    }
});

rvbd.widgets.yui3.PieWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.yui3.YUIWidget.apply(self, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.yui3.PieWidget.prototype = Object.create(rvbd.widgets.yui3.YUIWidget.prototype);

$.extend(rvbd.widgets.yui3.PieWidget.prototype, {
    requirements: ['charts-legend'],
    widgetClass: 'Chart'
});

rvbd.widgets.yui3.CandleStickWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.yui3.YUIWidget.apply(self, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.yui3.CandleStickWidget.prototype = Object.create(rvbd.widgets.yui3.YUIWidget.prototype);

$.extend(rvbd.widgets.yui3.CandleStickWidget.prototype, {
    requirements: ['series-candlestick', 'charts'],
    widgetClass: 'Chart',

    prepareData: function(data) {
        data.tooltip = {
            setTextFunction: function(textField, val) {
                textField.setHTML(val);
            },

            planarLabelFunction: function(cat, val, idx, s, sidx) {
                return data.dataProvider[idx].date + "<br>" +
                       "Open: " + data.dataProvider[idx].open.toString() + "<br>" +
                       "High: " + data.dataProvider[idx].high.toString() + "<br>" +
                       "Low: " + data.dataProvider[idx].low.toString() + "<br>" +
                       "Close: " + data.dataProvider[idx].close.toString();
            }
        };

        return data;
    }
});

})();
