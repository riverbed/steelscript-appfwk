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

window.run = function() {
    window.runRequested = true;
    $("#criteria").collapse('hide');
};

window.dorun = function() {
    if (!window.runRequested) {
        return;
    }
    window.runRequested = false;

    var $form = $('form#criteriaform');

    var criteria = $form.serializeArray();
    criteria.shift();
    criteria.splice(criteria.length - 2, 2);

    $('#id_debug').val(window.debugFlag ? 'on' : '');
    $('#form-error-info').empty();
    $('body').css('cursor', 'wait');

    $form.ajaxSubmit({
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
    });
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

/* Renders all widgets in the current report, or, if widgetId is provided,
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
        wId,
        opts;
    $.each(renderWidgets, function(i, w) {
        if (rownum !== w.row) {
            $row = $('<div></div>')
                .addClass('row-fluid')
                .appendTo($report);
            rownum = w.row;
        }

        wId = 'chart_' + w.widgetid;
        $('<div></div>')
            .attr('id', wId)
            .addClass('blackbox span' + (isEmbedded ? '12' : w.width))
            .text("Widget " + w.widgetid)
            .appendTo($row);

        opts = w.options || {};
        opts.height = w.height;

        new window[w.widgettype[0]][w.widgettype[1]](w.posturl, wId, opts, w.criteria);
        window.rvbd_status[w.posturl] = 'running';
    });

    var completeCallback = isEmbedded ? onEmbedWidgetComplete : onReportWidgetComplete;

    // wait a short period before checking widget status
    setTimeout(function() { monitorWidgetStatus(completeCallback, widgets); }, 100);
}

/**
 * checks if each widget is finished loading, and then calls the provided
 * onComplete() function passing the widget's info of the completed widget. 
 */
function monitorWidgetStatus(onComplete, widgets) {
    // Filter widgets down to unfinished ones, and run onComplete() on the ones
    // that are finished.
    widgets = $.grep(widgets, function(widget) {
        if (window.rvbd_status[widget.posturl] === 'complete') {
            onComplete(widget);
        } else if (window.rvbd_status[widget.posturl] !== 'error') {
            return true;
        }
    });

    // If there are still running widgets, monitor again in 0.5 seconds
    if (widgets) {
        setTimeout(function() { 
            monitorWidgetStatus(onComplete, widgets);
        }, 500);
        return;
    }

    if (window.rvbd_debug) { // No more widgets running and we're in debug mode
        alert('Complete - you will now be prompted to download a zipfile ' +
              'containing the server logs.');
        window.location = window.rvbd_debug_url;
    }
}

/**
 * Called after each widget in the report finishes loading
 */
function onReportWidgetComplete(widget) {
    var $chart_div = $('#chart_' + widget.widgetid),
        $title_div = $('#chart_' + widget.widgetid + '_content-title'),
        $content_div = $('#chart_' + widget.widgetid + '_content');
    addWidgetMenu(widget, $title_div);
}

/**
 * Called after an embedded widget finishes loading.
 */
function onEmbedWidgetComplete(widget) {
    /* var $chart_div = $('#chart_' + widget.widgetid),
        $title_div = $('#chart_' + widget.widgetid + '_content-title'),
        $content_div = $('#chart_' + widget.widgetid + '_content');

    // Code here... */
}

function addWidgetMenu(widget, $titleDiv) {
    var menuItems = [
        '<a tabindex="-1" id="' + widget.widgetid + '_get_embed">Embed This Widget...</a>'
    ];

    var $menuContainer = $('<div></div>')
            .attr('id', 'reports-dropdown')
            .addClass('dropdown'),
        $menuButton = $('<a></a>')
            .attr('id', widget.widgetid + '_menu')
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
                'aria-labelledby': widget.widgetid + '_menu'
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
                  .appendTo($titleDiv);

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
    var url = window.location.href.split('#')[0] +  'widget/' + widget.widgetid +
              '?' + $.param(criteria);

    // Add the actual menu item listener which triggers the modal
    $('#' + widget.widgetid + '_get_embed').click(function() {
        var iframe = generateIFrame(url, 500, widget.height + 12),
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
            // this function is called on 'shown' 
            
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

function updateTimeAndRun() {
    $('#timenow').click();
    run();
}

})();