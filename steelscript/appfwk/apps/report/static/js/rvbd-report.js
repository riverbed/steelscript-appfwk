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
        if (rownum !== w.row) {
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
    setTimeout(function(){ monitorWidgetStatus(onReportWidgetComplete, widgets); }, 100);
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
    widgets = $.grep(widgets, function(w) {
        if (w.widgetid !== widget_info.widgetid){
            return false;
        }
        if (rownum !== w.row) {
            row = $('<div />', { 'class': 'row-fluid' }).appendTo(report);
            rownum = w.row;
        }
        var wid = "chart_" + w.widgetid;
        $('<div />',
          { id: wid,
            'class': 'blackbox span12' })
            .text ("Widget " + w.widgetid)
            .appendTo(row);

        // replace the default criteria with the url criteria
        var url_criteria = JSON.parse(widget_info.criteria);
        w.criteria = $.extend(true, {}, w.criteria, url_criteria);

        var opts = w.options || {};
        opts.height = w.height;
        new global[w.widgettype[0]][w.widgettype[1]] ( w.posturl, wid, opts, w.criteria );
        rvbd_status[w.posturl] = 'running';
        return true;
    });

    // wait a short period before checking widget status
    setTimeout(function(){ monitorWidgetStatus(onEmbedWidgetComplete, widgets); }, 100);
}

/**
 * checks if each widget is finished loading, and then calls the provided
 * onComplete() function passing the widget's info of the completed widget. 
 */
function monitorWidgetStatus(onComplete, widgets) {
    var i, unfinished_widgets = [];
    for (i = 0; i < widgets.length; ++i) {
        if(global.rvbd_status[widgets[i].posturl] === 'complete'){
            onComplete(widgets[i]);
        }else if(global.rvbd_status[widgets[i].posturl] !== 'error'){
            unfinished_widgets.push(widgets[i]);
        }
    }
    widgets = unfinished_widgets;

    // if there are still running widgets, monitor widgets in 0.5 seconds
    if ( widgets.length !== 0) {
        setTimeout(function(){ 
            monitorWidgetStatus(onComplete, widgets); }, 
            500);
        return;
    }
    // all statuses are not 'running', trigger the zipfile download
    if (global.rvbd_debug === true) {
        alert('Complete - you will now be prompted to download a zipfile ' +
              'containing the server logs.');
        window.location = rvbd_debug_url;
    }
}

var onReportWidgetComplete = function (widget) {
    var $chart_div = $('#chart_' + widget.widgetid),
        $title_div = $('#chart_' + widget.widgetid + '_content-title'),
        $content_div = $('#chart_' + widget.widgetid + '_content');
    // Add functions to be called after each widget in the report finishes loading
    addWidgetMenu(widget, $title_div);
};

var onEmbedWidgetComplete = function (widget) {
    var $chart_div = $('#chart_' + widget.widgetid),
        $title_div = $('#chart_' + widget.widgetid + '_content-title'),
        $content_div = $('#chart_' + widget.widgetid + '_content');
    // Add functions to be called after embedded widget finishes loading
};

function addWidgetMenu(widget, $title_div) {
    var id = widget.widgetid;
    // a list of menu items
    var menu_items = [
        '<a tabindex="-1" id="'+id+'_get_embed">Get Embed Code</a>'
    ];

    // here we create all the html elements for our menu
    var $menu_container = $('<div>')
        .attr('class', 'dropdown')
        .css({
            position: 'relative',
            float: 'right',
            top: '0px;',
            height: '26px'
        });
    var $menu_button = $('<a>')
        .attr('class', 'dropdown-toggle')
        .attr('id', id+'_menu')
        .attr('data-toggle', 'dropdown')
        .attr('href', '#');
    var $menu_icon = $('<span>')
        .attr('class', 'icon-chevron-down');
    var $menu = $('<ul>')
        .attr('class', 'dropdown-menu')
        .attr('role', 'menu')
        .attr('aria-labelledby', id+'_menu')
        .css({
            left: 'auto',
            right: '0px'
        });

    // iterate over all the menu items, and add them to the menu
    var i; 
    for (i = 0; i < menu_items.length; ++i) {
        var $li = $('<li>')
            .attr('role', 'presentation');
        var $item = menu_items[i];
        $li.append($item);
        $menu.append($li);
    }

    // Now append the menu and the button to our menu container
    $menu_button.append($menu_icon);
    $menu_container.append($menu_button);
    $menu_container.append($menu);
    // Add the menu to the widget!
    $title_div.append($menu_container);

    // Add menu item onClick handlers
    addGetEmbedHtmlHandler(widget);
}

function addGetEmbedHtmlHandler(widget){
    // Create the url that describes the current widget
    var url = window.location.href;
    url = url.replace(window.location.hash, "").replace("#", "");
    url += 'widget/' + widget.widgetid + '?';
    var criteria = widget.criteria;
    for (var key in criteria) {
        if (criteria.hasOwnProperty(key)) {
            var param = encodeURIComponent(key);
            var value = encodeURIComponent(criteria[key]);
            url += param + '=' + value + '&';
        }
    }
    // Helper function for generating an iframe from a url and width and height
    function generateIFrame(url, width, height){
        return '<iframe width="'+ width + '" height="' + height +
            '" src="' + url + 
            '" frameborder="0"></iframe>';
    }
    // Add the actual menu item listener which triggers the modal
    $('#'+widget.widgetid+'_get_embed').click(function() {
        var iframe = generateIFrame(url, 500, widget.height + 12); 
        var body = 'Choose dimensions for the embedded widget:<br>' +
            '<table>' +
            '<tr>' +
              '<td><h4>Width:</h4></td>' +
              '<td><input value="500" type="text" id="widget-width"' + 
                    'style="width:50px;margin-top:10px;"></td>' +
            '</tr>' +
            '<tr>' +
              '<td><h4>Height:</h4></td>' +
              '<td><input value="312" type="text" id="widget-height" ' +
                    'style="width:50px;margin-top:10px;"></td>' +
            '</tr>' +
            '</table><br>Copy the following HTML to embed the widget:' +
            '<input id="embed_text" value=\'' + iframe + 
            '\' type="text" style="width:97%">';
        var heading = 'Embed Widget HTML';
        var okButtonTxt = 'OK';
        alertModal(heading, body, okButtonTxt, function(){
            // this function is called on 'shown' 
            
            // automatically set the focus to the iframe text
            $('#embed_text').focus(function(){ this.select(); });
            $('#embed_text').mouseup(function(){ this.select(); });
            $('#embed_text').focus();

            // update the iframe to reflect the width and height fields
            $('#widget-width').keyup(function(){
                var new_iframe = generateIFrame(url, 
                    $(this).val(), $('#widget-height').val()); 
                $('#embed_text').attr('value', new_iframe);
            });
            $('#widget-height').keyup(function(){
                var new_iframe = generateIFrame(url, 
                    $('#widget-width').val(), $(this).val()); 
                $('#embed_text').attr('value', new_iframe);
            });
        });
    });
}

function showEmbedPopup(url){
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
    var form = $('form#criteriaform');
    // save a copy of the criteria for future reference when embedding
    var criteria = form.serializeArray();
    criteria.shift();
    criteria.splice(criteria.length - 2, 2);
    $("body").css("cursor", "wait");
    form.ajaxSubmit({
        dataType:"json",
        type: "post",
        url: form.attr('action'),
        success: function(data, textStatus) {
            $("body").css("cursor", "default");
            renderReport(data, criteria);
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

