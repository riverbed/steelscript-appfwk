/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

// This script is used by report.html and widget.html to create the graphs/widgets

var global = this;
var rvbd_status = {};
var rvbd_debug = false;
var rvbd_debug_url = '';

// used for auto-run and widgets. If widget_info is not provided,
// then it is assumed that the renderPage() call was used for an
// auto-run report, not a stand-alone widget. If it is provided, call
// renderWidget(), instead of renderReport().
function renderPage(widgets_url, widget_info) {
    $.ajax({
        dataType:"json",
        type: "get",
        url: widgets_url,
        success: function(data, textStatus, jqXHR) {
            if (widget_info){
              renderWidget(data, widget_info);
            }else{
              renderReport(data);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // we receive a 400 error on form validation problems
            if (jqXHR.status == 400) {
                alert("an error occurred: " + textStatus + " : " + errorThrown);
            }
            if (jqXHR.status == 500) {
                alert("an error occurred: " + textStatus + " : " + errorThrown);
            }
        }
    });
}

// renderReport() renders all the widgets in the current report
function renderReport(widgets) {
    // reset the status
    global.rvbd_status = {};

    // pull first element off list which contains information about the report
    var report_meta = widgets.shift();
    $('#report_datetime').html(report_meta.datetime);
    $('#report_timezone').html(report_meta.timezone);
    rvbd_debug = report_meta.debug;

    var report=$("#report");
    report.html(widgets);
    var rownum=0;
    var row;
    $.each(widgets, function(i,w) {
        if (rownum != w.row) {
            row = $('<div />', { 'class': 'row-fluid' }).appendTo(report);
            rownum = w.row;
        }
        var wid = "chart_" + w.widgetid;
        $('<div />',
          { id: wid,
            'class': 'blackbox span' + w.width })
            .text ("Widget " + w.widgetid)
            .appendTo(row);

        var opts = w.options || {};
        opts.height = w.height;
        new global[w.widgettype[0]][w.widgettype[1]] ( w.posturl, wid, opts, w.criteria );
        rvbd_status[w.posturl] = 'running';
    });

    // wait a short period before checking widget status
    setTimeout(monitorWidgetStatus, 100);
}

// renderWidget() is very similar to renderReport(), but it makes sure to only render
// one widget, (the one whose id == widget_info.widgetid)
function renderWidget(widgets, widget_info) {
    // reset the status
    global.rvbd_status = {};

    // pull first element off list which contains information about the report
    var report_meta = widgets.shift();
    $('#report_datetime').html(report_meta.datetime);
    $('#report_timezone').html(report_meta.timezone);

    var report=$("#report");
    report.html(widgets);
    var rownum=0;
    var row;

    // run through all the report's widgets, if the widget isn't the one we are
    // looking for, then stop there, and if it is, generate the HTML to display it
    $.each(widgets, function(i,w) {
        if (w.widgetid != widget_info.widgetid){
              return true;
        }
        if (rownum != w.row) {
            row = $('<div />', { 'class': 'row-fluid' }).appendTo(report);
            rownum = w.row;
        }
        var wid = "chart_" + w.widgetid;
        $('<div />',
          { id: wid,
            'class': 'blackbox span12' })
            .text ("Widget " + w.widgetid)
            .appendTo(row);

        var url_criteria = JSON.parse(widget_info.criteria);
        var criteria = $.extend(true, {}, w.criteria, url_criteria);

        var opts = w.options || {};
        opts.height = w.height;
        new global[w.widgettype[0]][w.widgettype[1]] ( w.posturl, wid, opts, criteria );
        rvbd_status[w.posturl] = 'running';
    });

    // wait a short period before checking widget status
    setTimeout(monitorWidgetStatus, 100);
}

function monitorWidgetStatus() {
    // keep checking while at least one widget is running
    for (var key in global.rvbd_status) {
        if (global.rvbd_status[key] == 'running') {
            setTimeout(monitorWidgetStatus, 500);
            return;
        };
    };
    // all statuses are not 'running', trigger the zipfile download
    if (global.rvbd_debug == true) {
        alert('Complete - you will now be prompted to download a zipfile ' +
              'containing the server logs.');
        window.location = rvbd_debug_url;
    };
}

function updateTimeAndRun() {
    $('#timenow').click();
    run();
}

function run() {
    runRequested = true;
    $("#criteria").collapse('hide');
}

function runDebug() {
    debugFlag = true;
    run();
}

function dorun() {
    if (!runRequested)
        return;
    runRequested = false;
    $("#id_debug").val(debugFlag ? "on" : "");
    $("#form-error-info").html("");
    form = $('form#criteriaform');
    $("body").css("cursor", "wait");
    form.ajaxSubmit({
        dataType:"json",
        type: "post",
        url: form.attr('action'),
        success: function(data, textStatus) {
            $("body").css("cursor", "default");
            renderReport(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // we receive a 400 error on form validation problems
            $("body").css("cursor", "default");
            if (jqXHR.status == 400) {
                $("#criteria").collapse('show');
                $("#form-error-info").html(jqXHR.responseText);
            }
            if (jqXHR.status == 500) {
                alert("an error occurred: " + textStatus + " : " + errorThrown);
            }
        }
    });
    debugFlag = false;
}

function update_criteria(data) {
    $.each(data, function(i,w) {
        //alert('Updating ' + i + ',' + w + ' #' + w.id + '-span' + '\n' + w.html);
        $('#' + w.id + '-span').html(w.html);
    });
}
function criteria_changed() {
    $("body").css("cursor", "wait");
    form = $('form#criteriaform');
    form.ajaxSubmit({
        dataType:"json",
        type: "post",
        url: form.attr('action') + 'criteria/',
        success: function(data, textStatus) {
            $("body").css("cursor", "default");
            update_criteria(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            $("body").css("cursor", "default");
            alert("Failed: jqXHR: " + jqXHR.status + "\ntextStatus: " + textStatus);

            // we receive a 400 error on form validation problems
            if (jqXHR.status == 400) {
                $("#criteria").collapse('show');
                $("#form-error-info").html(jqXHR.responseText);
            }
            if (jqXHR.status == 500) {
                alert("an error occurred: " + textStatus + " : " + errorThrown);
            }
        }
    });
}

