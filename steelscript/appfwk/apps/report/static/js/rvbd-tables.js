/**
 # Copyright (c) 2016 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the MIT License
 # accompanying the software ("License").  This software is distributed "AS IS"
 # as set forth in the License.
 */

(function() {
'use strict';

rvbd.widgets.tables = {};

rvbd.widgets.tables.DataTableWidget = function(postUrl, isEmbedded, div,
                                               id, slug, options, criteria, dataCache) {
    var self = this;

    var ct = $(window);
    ct.resize(function() { self.onResize(); });

    rvbd.widgets.Widget.apply(self, [postUrl, isEmbedded, div,
                                     id, slug, options, criteria, dataCache]);
};

/* Pivot Widget base class */
rvbd.widgets.tables.DataTableWidget.prototype = Object.create(rvbd.widgets.Widget.prototype);

$.extend(rvbd.widgets.tables.DataTableWidget.prototype, {
    prepareData: function(data) {
        $.each(data.columns, function(i, c) {
            var formatter;
            if (c.formatter) {
                if (c.formatter in rvbd.formatters) {
                    formatter = rvbd.formatters[c.formatter];
                } else {
                    formatter = eval(c.formatter);
                }
                // DataTables uses the 'render' attr for formatters
                c.render = (function(key, formatter) {
                    return function(data, type, row) {
                        if (type === 'display') {
                            return formatter(data);
                        }
                        // for all other queries, return default data
                        return data;
                    }
                })(c.key, formatter);
            }
        });

        return data;
    },

    render: function(data) {
        var self = this;
        self.data = data;

        self.titleMsg = data['chartTitle'];
        self.buildInnerLayout();

        data = self.prepareData(data);
        self.data = data;

        self.onRender();
    },

    /* Called immediately after render after the widget is created. */
    onRender: function() {
        // Behavior implemented in subclasses
    },

    /* Called when the widget is resized (or created) */
    onResize: function() {
        var self = this;
        self.render(self.data);
    },

});

/**
 *
 * TableWidget -- uses underlying DataTables js renderer
 *
 */

rvbd.widgets.tables.TableWidget = function(postUrl, isEmbedded, div,
                                           id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.tables.DataTableWidget.apply(self, [postUrl, isEmbedded, div,
                                              id, slug, options, criteria, dataCache]);
};
rvbd.widgets.tables.TableWidget.prototype = Object.create(rvbd.widgets.tables.DataTableWidget.prototype);

$.extend(rvbd.widgets.tables.TableWidget.prototype, {
    onRender: function() {
        var self = this;
        var $content = $(self.content);
        var $table = $('<table></table>')
            .attr('id', self.id + '_datatable')
            .addClass('display')
            .addClass('compact');
        var options = self.data.options;

        $content.append($table);

        if (options.scrollY) {
            var height = ($(self.outerContainer).height() - self.contentExtraHeight - self.titleHeight);

            // subtract datatable header
            height = height - 30;

            // take into account additional stuff around table
            if (options.paging) {
                height = height - 85;
            } else {
                if (options.info) {
                    height = height - 35;
                }
                if (options.searching) {
                    height = height - 50;
                }
            }
            options.scrollY = height;
        }

        $table.DataTable({
            data: self.data.data,
            columns: self.data.columns,
            info: options.info,
            lengthChange: options.lengthChange,
            paging: options.paging,
            scrollY: options.scrollY,
            searching: options.searching,
            // we get our data ordered already from the server side
            // don't apply any ordering within the widget init
            order: []
        });

        // apply any tooltips that have been created inside table
        $('.tooltip-class').tooltip();
    }
});

/**
 *
 * PivotTableWidget -- uses underlying PivotTables js renderer
 *
 */

rvbd.widgets.tables.PivotTableWidget = function(postUrl, isEmbedded, div,
                                                id, slug, options, criteria, dataCache) {
    var self = this;

    rvbd.widgets.tables.DataTableWidget.apply(self, [postUrl, isEmbedded, div,
                                                     id, slug, options, criteria, dataCache]);
};
rvbd.widgets.tables.PivotTableWidget.prototype = Object.create(rvbd.widgets.tables.DataTableWidget.prototype);

$.extend(rvbd.widgets.tables.PivotTableWidget.prototype, {
    onRender: function() {
        var self = this;
        var $content = $(self.content);
        $content.pivotUI(
            self.data.data
        );
    }
});

})();
