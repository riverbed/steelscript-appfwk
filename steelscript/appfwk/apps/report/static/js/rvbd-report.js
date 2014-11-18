/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

// This script is used by report.html and widget.html to create the graphs/widgets
rvbd_status = {};
rvbd_debug = false;
rvbd_debug_url = '';

(function() {
'use strict';

window.launchPrintWindow = function() {
    function doLaunch(expandTables) {
        var $form = $('#criteriaform');
        var origAction = $form.attr('action');

        $form.attr('action', origAction + 'print/');

        $('#id_expand_tables').val(expandTables ? 'on' : '');

        window.launchingPrintWindow = true;
        $('#criteriaform').submit();
        window.launchingPrintWindow = false;

        $form.attr('action', origAction);
    }

    var oversizedTablesFound = false;
    $('.yui3-datatable-y-scroller').each(function() {
        if (this.scrollHeight > this.clientHeight) {
            oversizedTablesFound = true;
            return;
        }
    });

    if (oversizedTablesFound) {
        var okCallback = function() { doLaunch(true); },
            cancelCallback = function() { doLaunch(false); },
            content = "Some table(s) contain too much content to fit at standard height " +
                      "and will be cut off. Would you like to extend these tables vertically " +
                      "to show all data?";
        confirm("Print report", content, "Don't extend", "Extend", okCallback, cancelCallback);
    } else {
        doLaunch(false);
    }
}

// If widgetInfo is provided, renders an embedded widget. Otherwise, renders
// the whole report.
window.renderPage = function(widgetsUrl, widgetInfo) {
    $.ajax({
        dataType: 'json',
        type: 'get',
        url: widgetsUrl,
        success: function(data, textStatus, jqXHR) {
            renderWidgets(data, widgetInfo);
        },
        error: function(jqXHR, textStatus, errorThrown) { 
            alertReportError(textStatus, errorThrown);
        }
    });
}

window.criteria_changed = function() {
    $('body').css('cursor', 'wait');
    window.form = $('form#criteriaform');
    window.form.ajaxSubmit({
        dataType: 'json',
        type: 'post',
        url: form.attr('action') + 'criteria/',
        complete: function(data, textStatus, jqXHR) {
            $('body').css('cursor', 'default');
        },
        success: function(data, textStatus) {
            update_criteria(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            if (jqXHR.status === 400) { // Form validation problems
                $('#criteria').collapse('show');
                $('#form-error-info').html(jqXHR.responseText);
            } else {
                alertReportError(textStatus, errorThrown);
            }
        }
    });
};

window.enablePrintButton = function() {
    $('<a href="#" class="icon-print print-report" title="Print this report"></a>')
         .click(window.launchPrintWindow)
         .replaceAll('.print-report');
}

window.disablePrintButton = function() {
    $('<span class="icon-print print-report" title="Print this report (run report to enable)"></span>')
         .replaceAll('.print-report');
}

window.run = function() {
    window.runRequested = true;
    $("#criteria").collapse('hide');
};

window.updateTimeAndRun = function() {
    $('#timenow').click();
    run();
}

window.dorun = function() {
    if (!window.runRequested) {
        return;
    }
    window.runRequested = false;

    window.disablePrintButton();

    var $form = $('form#criteriaform'),
        ajaxParams = {
            dataType: 'json',
            type: 'post',
            url: $form.attr('action'),
            complete: function(jqXHR, textStatus) {
                $('body').css('cursor', 'default');
            },
            success: function(data, textStatus) {
                renderWidgets(data);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                if (jqXHR.status === 400) {
                    $('#criteria').collapse('show');
                    $('#form-error-info').html(jqXHR.responseText);
                } else {
                    alertReportError(textStatus, errorThrown);
                }
            }
        };

    if (typeof window.autoLoadCriteria !== 'undefined'
        && window.autoLoadCriteria !== null) { // Criteria already provided (print view)
        ajaxParams.data = window.autoLoadCriteria;
        $.ajax(ajaxParams);
    } else { // Standard form submit
        $form.ajaxSubmit(ajaxParams);
    }

    $('#id_debug').val(window.debugFlag ? 'on' : '');
    $('#form-error-info').empty();
    $('body').css('cursor', 'wait');

    window.debugFlag = false;
}

function update_criteria(data) {
    $.each(data, function(i, w) {
        $('#' + w.id + '-span').html(w.html);
    });
}

/**
 * Call to alert the user when we receive a server error from a report-wide
 * problem (e.g., invalid criteria).
 */
function alertReportError(textStatus, errorThrown) {
    alert("An error occurred: " + textStatus + ": " + errorThrown)
}

/* Renders all widgets in the current report, or, if widgetInfo is provided,
   just that widget. */
function renderWidgets(widgets, widgetInfo) {
    var $report = $('#report'),
        isEmbedded = (typeof widgetInfo !== 'undefined'),
        report_meta,
        renderWidgets;

    // reset the status
    window.rvbd_status = {};

    // pull first element off list which contains information about the report
    report_meta = widgets.shift();

    window.rvbd_debug = report_meta.debug;

    $('#report_datetime').html(report_meta.datetime);
    $('#report_timezone').html(report_meta.timezone);

    $report.html(widgets);

    if (!isEmbedded) { // Full report
        renderWidgets = widgets;
    } else { // Embedded widget
        // Find the widget we want to render
        var targetWidget;
        $.each(widgets, function(i, widget) {
            if (widget.widgetid === widgetInfo.widgetid) {
                targetWidget = widget;
                return false;
            }
        })

        // Replace the default criteria with the criteria from the widget request URL.
        $.extend(targetWidget.criteria, JSON.parse(widgetInfo.criteria));

        renderWidgets = [targetWidget];
    }

    var $row,
        rownum = 0,
        opts;
    $.each(renderWidgets, function(i, w) {
        if (rownum !== w.row) {
            $row = $('<div></div>')
                .addClass('row-fluid')
                .appendTo($report);
            rownum = w.row;
        }

        // Create empty div that the new widget object will populate
        var $div = $('<div></div>')
            .appendTo($row);

        opts = w.options || {};
        opts.height = w.height;
        opts.width = w.width;

        var widgetModule = w.widgettype[0],
            widgetClass = w.widgettype[1];

        new window[widgetModule][widgetClass](w.posturl, isEmbedded, $div[0],
                                              w.widgetid, opts, w.criteria);
        window.rvbd_status[w.posturl] = 'running';
    });

    var completeCallback = (isEmbedded ? onEmbedWidgetComplete : onReportWidgetComplete);

    $(document).on('widgetDoneLoading', function(e, widget) { 
        completeCallback(widget);
        checkAndProcessCompleteWidgets();
    });
}

function checkAndProcessCompleteWidgets() {
    var widgetsRunning = false;
    $.each(window.rvbd_status, function(postUrl, status) {
        if (status === 'running') {
            widgetsRunning = true;
            return;
        }
    });

    if (!widgetsRunning) {
        if (window.rvbd_debug) {
            alert('Complete - you will now be prompted to download a zipfile ' +
                  'containing the server logs.');
            window.location = window.rvbd_debug_url;
        }

        window.enablePrintButton();
    }
}

/**
 * Called after each widget in the report finishes loading
 */
function onReportWidgetComplete(widget) {
    addWidgetMenu(widget);
}

/**
 * Called after an embedded widget finishes loading.
 */
function onEmbedWidgetComplete(widget) {
    // Code here...
}

function addWidgetMenu(widget) {
    var id = widget.id;

    var menuItems = [
        '<a tabindex="-1" id="' + id + '_get_embed">Embed This Widget...</a>'
    ];

    var $menuContainer = $('<div></div>')
            .attr('id', 'reports-dropdown')
            .addClass('dropdown'),
        $menuButton = $('<a></a>')
            .attr('id', id + '_menu')
            .addClass('dropdown-toggle widget-dropdown-toggle')
            .attr({
                href: '#',
                'data-toggle': 'dropdown'
            }),
        $menuIcon = $('<span></span>')
            .addClass('icon-chevron-down'),
        $menu = $('<ul></ul>')
            .addClass('dropdown-menu widget-dropdown-menu')
            .attr({
                role: 'menu',
                'aria-labelledby': id + '_menu'
            });

    // Add each menu item to the menu
    $.each(menuItems, function(i, menuItem) {
        $('<li></li>').attr('role', 'presentation')
                      .html(menuItem)
                      .appendTo($menu);
    });

    // Append the menu and the button to our menu container, then add the menu
    // to the widget.
    $menuButton.append($menuIcon);
    $menuContainer.append($menuButton)
                  .append($menu)
                  .appendTo($('#chart_' + id + '_content-title'));

    // Add menu item onClick handlers
    addGetEmbedHtmlHandler(widget);
}

function addGetEmbedHtmlHandler(widget) {
    function generateIFrame(url, width, height){
        // Helper function for generating an iframe from a url and width and height
        return '<iframe width="'+ width + '" height="' + height +
               '" src="' + url + '" frameborder="0"></iframe>';
    }

    // Create the url that describes the current widget
    var criteria = $.extend({}, widget.criteria);

    // Delete starttime and endtime from params if present (we don't want embedded
    // widgets with fixed time frames)
    delete criteria.starttime;
    delete criteria.endtime;

    // Create the url that describes the current widget
    var url = window.location.href.split('#')[0] + 'widget/' + widget.id +
              '?' + $.param(criteria);

    // Add the actual menu item listener which triggers the modal
    $('#' + widget.id + '_get_embed').click(function() {
        var iframe = generateIFrame(url, 500, widget.options.height + 12),
            heading = "Embed Widget HTML",
            okButtonTxt = "OK",
            body = 'Choose dimensions for the embedded widget:<br>' +
                   '<table>' +
                   '<tr>' +
                       '<td><h4>Width:</h4></td>' +
                       '<td><input value="500" type="text" id="widget-width" ' + 
                                  'style="width:50px;margin-top:10px;"></td>' +
                    '</tr>' +
                    '<tr>' +
                        '<td><h4>Height:</h4></td>' +
                        '<td><input value="312" type="text" id="widget-height" ' +
                                   'style="width:50px;margin-top:10px;"></td>' +
                    '</tr>' +
                    '</table><br>Copy the following HTML to embed the widget:' +
                    '<input id="embed_text" value="' + iframe.replace(/"/g, '&quot;') + 
                    '" type="text" style="width:97%">';

        alertModal(heading, body, okButtonTxt, function() {
            // automatically set the focus to the iframe text
            $('#embed_text')
                .on('mouseup focus', function() { this.select(); })
                .focus();

            // update the iframe to reflect the width and height fields
            $('#widget-width, #widget-height').keyup(function(){
                $('#embed_text').attr('value', generateIFrame(url, $('#widget-width').val(),
                                                                   $('#widget-height').val()));
            });
        });
    });
}

})();