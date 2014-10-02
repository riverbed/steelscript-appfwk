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

window.rvbd_yui3 = {};

window.rvbd_yui3.YUIWidget = function(dataurl, divid, options, criteria) {
    var self = this;

    Widget.apply(self, [dataurl, divid, options, criteria]);
};
window.rvbd_yui3.YUIWidget.prototype = Object.create(Widget.prototype);
$.extend(window.rvbd_yui3.YUIWidget.prototype, {
    buildInnerLayout: function(title) {
        var self = this;

        var $div = $(self.div);

        self.title = $('<div></div>')
            .attr('id', $div.attr('id') + '_content-title')
            .html(title)
            .addClass('widget-title yui-widget-title'),
        self.content = $('<div></div>')
            .attr('id', $div.attr('id') + '_content')
            .addClass('yui3-skin-sam yui-widget-content');

        self.outerContainer = $('<div></div>')
            .addClass('yui-widget-outer-container')
            .append($(self.title))
            .append($(self.content));

        $div.empty()
            .append(self.outerContainer);
    },

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

    prepareData: function(data) {
        return data;
    },

    onResize: function() {
        var self = this;

        // YUI widgets don't resize their content automatically when the size of their DIV changes.
        // For most (all?) widgets, we can just manually re-set their size and they'll automatically
        // re-render. (Resizing with JS also makes it easy to make the content DIV fill up all of the
        // remainining space after the title bar, which is tricky with pure CSS.)

        var width = $(self.outerContainer).width() - self.contentExtraWidth,
            height = $(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight;

        if (self.widgetClass === 'Chart') {
            self.yuiWidget.set('width', width);
            self.yuiWidget.set('height', height);
        } else {
            self.yuiWidget.set('width', String(width) + 'px');
            self.yuiWidget.set('height', String(height) + 'px');
        }
    },

    render: function(data) {
        var self = this;

        self.buildInnerLayout(data.chartTitle);

        var $content = $(self.content)
        self.contentExtraWidth  = parseInt($content.css('margin-left'), 10) +
                                  parseInt($content.css('margin-right'), 10);
        self.contentExtraHeight = parseInt($content.css('margin-top'), 10) +
                                  parseInt($content.css('margin-bottom'), 10);
        self.titleHeight  = $(self.title).outerHeight();


        data = self.addBasicParams(data);
        data = self.prepareData(data);
        self.data = data;

        var requirements = self.requirements.concat(['event-resize']); // All widgets need event-resize
        YUI().use(requirements, function(Y) {
            self.yuiWidget = new Y[self.widgetClass](data);

            Y.on('windowresize', self.onResize.bind(self));
        });
    }
});


window.rvbd_yui3.TableWidget = function (dataurl, divid, options, criteria) {
    var self = this;

    window.rvbd_yui3.YUIWidget.apply(self, [dataurl, divid, options, criteria]);
};
window.rvbd_yui3.TableWidget.prototype = Object.create(window.rvbd_yui3.YUIWidget.prototype);

$.extend(window.rvbd_yui3.TableWidget.prototype, {
    requirements: ['datatable-scroll', 'datatable-sort'],
    widgetClass: 'DataTable',

    prepareData: function(data) {
        data.scrollable = 'xy';
        $.each(data.columns, function(i, c) {
            if (typeof c.formatter !== 'undefined' && c.formatter in window.rvbd_yui3.YUIWidget.prototype) {
                c.formatter = (function(key, f) {
                    return function(v) { return f.call(window.rvbd_yui3.TableWidget.prototype, v.data[key]); }
                })(c.key, Widget.prototype[c.formatter]);
            } else {
                delete c.formatter;
            }
        });

        return data;
    }
});


window.rvbd_yui3.TimeSeriesWidget = function(dataurl, divid, options, criteria) {
    var self = this;

    window.rvbd_yui3.YUIWidget.apply(self, [dataurl, divid, options, criteria]);
};
window.rvbd_yui3.TimeSeriesWidget.prototype = Object.create(window.rvbd_yui3.YUIWidget.prototype);

$.extend(window.rvbd_yui3.TimeSeriesWidget.prototype, {
    requirements: ['charts-legend'],
    widgetClass: 'Chart',

    prepareData: function(data) {
        var self = this;

        $.each(data.axes, function(i, axis) {
            if ('formatter' in axis) {
                axis.labelFunction = (function(formatter) {
                    return function (v, fmt, tooltip) {
                        return formatter.call(window.rvbd_yui3.TimeSeriesWidget.prototype,
                                              v, tooltip ? 2 : 1);
                    }
                })(window.rvbd_yui3.YUIWidget.prototype[axis.formatter]);
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

window.rvbd_yui3.ChartWidget = function(dataurl, divid, options, criteria) {
    var self = this;

    window.rvbd_yui3.YUIWidget.apply(self, [dataurl, divid, options, criteria]);
};

window.rvbd_yui3.ChartWidget.prototype = Object.create(window.rvbd_yui3.YUIWidget.prototype);
$.extend(window.rvbd_yui3.ChartWidget.prototype, {
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

window.rvbd_yui3.PieWidget = function(dataurl, divid, options, criteria) {
    var self = this;

    window.rvbd_yui3.YUIWidget.apply(self, [dataurl, divid, options, criteria]);
};

window.rvbd_yui3.PieWidget.prototype = Object.create(window.rvbd_yui3.YUIWidget.prototype);
$.extend(window.rvbd_yui3.PieWidget.prototype, {
    requirements: ['charts-legend'],
    widgetClass: 'Chart'
});

})();