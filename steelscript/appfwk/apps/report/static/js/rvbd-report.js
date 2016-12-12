/**
 # Copyright (c) 2016 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the MIT License
 # accompanying the software ("License").  This software is distributed "AS IS"
 # as set forth in the License.
 */

(function() {
'use strict';

/**
 * Stores all methods connected to rendering reports and embedded widgets,
 * as well as all state for the current report/embedded widget display.
 */
rvbd.report = {
    widgets: [],
    debug: false,

    runRequested: false,
    debugFlag: false,
    launchingPrintWindow: false,

    intervalID: 0,              // ID to manage scheduled reports
    needs_reload_scheduled: false,
    reportHasRendered: false,

    /**
     * HTML5 local storage and history methods
     */
    supports_history_api: function() {
        return !!(window.history && history.pushState);
    },

    getLocalStorage: function(key) {
        var data = window.localStorage.getItem(key);
        if (!data) {
            return;
        }
        return JSON.parse(data);
    },

    setLocalStorage: function(key, value) {
        // don't overwrite an existing key
        var data = window.localStorage.getItem(key);
        if (!data) {
            try {
                window.localStorage.setItem(key, JSON.stringify(value));
                console.log('setLocalStorage: First Attempt Save!');
                return true;
            } catch(out_err) {
                // Remove all items and try again
                try {
                    window.localStorage.clear();
                    console.log('setLocalStorage: localStorage cleared!');
                    window.localStorage.setItem(key, JSON.stringify(value));
                    console.log('setLocalStorage: Second Attempt Save!');
                    return true;
                } catch(in_err) {
                    console.log('setLocalStorage: All Saves Failed!');
                    return false;
                }
            }
        } else {
            console.log('setLocalStorage: Data Already Present!');
            return true;
        }

    },

    saveState: function(hash, data) {
        // add location hash and corresponding local storage
        if (rvbd.report.supports_history_api() &&
            rvbd.report.setLocalStorage(hash, data)) {
            history.pushState(null, window.document.title, '#!' + hash)
        }
    },

    loadState: function() {
        // load state from hash in URL
        if (rvbd.report.supports_history_api()) {
            var hash = location.hash.replace('#!', '');
            var data = rvbd.report.getLocalStorage(hash);

            if (data) {
                rvbd.report.runRequested = false;
                $("#criteria").collapse('hide'); // self.doRunReport() triggers on this element being hidden

                // empty and show the report view
                $("#report").empty().show();
                $("#report-container").collapse('show');

                rvbd.report.renderWidgets(data);
                rvbd.report.updateReportDateTime(data.meta.lastUpdate.datetime,
                                                 data.meta.lastUpdate.timezone);

                rvbd.report.enablePrintButton();
                rvbd.report.enableReloadButton();
            }
        }
    },


    /**
     * Called after DOM load to set up and launch report (or embedded widget).
     */
    start: function() {
        $.ajaxSetup({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', rvbd.report.csrfToken);
                xhr.setRequestHeader('X-AuthToken', rvbd.report.authToken);
            }
        });

        if (rvbd.report.isEmbedded) { // We already have the widget spec data, so launch right away
            rvbd.report.runFixedCriteriaReport();
        } else if (rvbd.report.reloadMinutes > 0 && !rvbd.report.live) { // Auto-run report (updates at intervals)
            if (rvbd.report.static) {
                $("#criteria-row").hide();
            }
            rvbd.report.needs_reload_scheduled = true;
            rvbd.report.runFixedCriteriaReport();
        } else if (rvbd.report.static && !rvbd.report.live) { // Non-reloading static report
            $("#criteria-row").hide();
            rvbd.report.runFixedCriteriaReport();
        } else if (typeof rvbd.report.printCriteria !== 'undefined') { // We're in print view, so launch right away
            rvbd.report.doRunFormReport(false);
        } else { // Standard report
            var $form = $('#criteria-form');

            $form.submit(function() {
                // If not launching print window, run report. If launching print window,
                // allow standard POST request.
                if (!rvbd.report.launchingPrintWindow) {
                    rvbd.report.runFormReport();
                    return false;
                }
            });

            // Attach handlers for "Run" button/menu
            $('#button-run').click(function() { $form.submit(); });

            $('#menu-debug').click(function() {
                    rvbd.report.debugFlag = true;
                    $form.submit();
            });
            $('#menu-update-time-run').click(function() {
                $('#timenow_endtime_1, #datenow_endtime_1').click();
                $form.submit();
            });
            $('#menu-run').click(function() { $form.submit(); });

            $("#criteria").on('hide.bs.collapse', rvbd.report.doRunFormReport);

            if (rvbd.report.autoRun) { //Auto run report from bookmark
                $form.submit();
            } else {
                // load from state if we aren't autorun on initial load
                rvbd.report.loadState();
            }

            // add handler when navigation happens to refresh state
            window.addEventListener('popstate', function(event) {
                console.log('popstate fired!');
                if (location.href.endsWith("#")) {
                    console.log('ignoring, url ends with #');
                    // ignore it
                } else if (location.hash.replace('#!', '') == "") {
                    // reset view
                    $('#report-container').collapse('hide');
                    $('#criteria').collapse('show');
                } else {
                    rvbd.report.loadState();
                }
            });
        }
    },

    /**
     * Launches print view in new window. If there are oversized tables, prompts
     * the user to see if they want to have them expanded in the final output.
     */
    launchPrintWindow: function() {
        function doLaunch(expandTables) {
            var $form = $('#criteria-form');
            var origAction = $form.attr('action');

            $form.attr('action', origAction + 'print/');

            $('#id_expand_tables').val(expandTables ? 'on' : '');

            // The submit handler on the criteria form checks launchingPrintWindow
            // and allows a standard POST submit if it's true.
            rvbd.report.launchingPrintWindow = true;
            $form.submit();
            rvbd.report.launchingPrintWindow = false;

            $form.attr('action', origAction);
        }

        var oversizedTablesFound = false;
        $.each(rvbd.report.widgets, function(i, widget) {
            if (widget.isOversized()) {
                oversizedTablesFound = true;
            }
        });

        if (oversizedTablesFound) {
            var okCallback = function() { doLaunch(true); },
                cancelCallback = function() { doLaunch(false); },
                content = "Some table(s) contain too much content to fit at standard height " +
                          "and will be cut off. Would you like to extend these tables vertically " +
                          "to show all data?";
            rvbd.modal.confirm("Print report", content, "Don't extend", "Extend", okCallback, cancelCallback);
        } else {
            doLaunch(false);
        }
    },

    /**
     * Launch a report based on fixed criteria (i.e. auto-run or embedded widget).
     */
    runFixedCriteriaReport: function() {
        $.ajax({
            dataType: 'json',
            type: 'get',
            url: rvbd.report.widgetsUrl,
            success: function(data, textStatus, jqXHR) {
                rvbd.report.renderWidgets(data);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                rvbd.report.alertReportError(textStatus, errorThrown);
            }
        });
    },

    /**
     * Schedule the time for auto-reloads based on given offset
     */
    setSchedule: function () {
        var interval = rvbd.report.reloadMinutes * 60 * 1000;

        // trigger the reload, then schedule update
        if (rvbd.report.static) {
            rvbd.report.runFixedCriteriaReport();
            rvbd.report.intervalID = setInterval(rvbd.report.runFixedCriteriaReport, interval);
        } else {
            rvbd.report.reloadAllWidgets();
            rvbd.report.intervalID = setInterval(rvbd.report.reloadAllWidgets, interval);
        }
    },

    scheduleReloads: function (datetime) {
        var interval = rvbd.report.reloadMinutes * 60 * 1000;
        var offset = rvbd.report.offsetSeconds * 1000;

        if (offset == 0 || offset > interval) {
            // we can just setInterval, no need to be precise
            rvbd.report.intervalID = setInterval(rvbd.report.reloadAllWidgets, interval);
        } else {
            // need to set a timeout to align with offset then set the interval
            // assumes string datetime similar to:
            // "20th November 15:34:23"
            var date_parts = datetime.split(' '),
                time_parts = date_parts[3].split(':'),
                now = new Date(Date.now()),
                report_date,
                next_date;

            // construct date object from report datetime
            report_date = new Date(now.getFullYear(), now.getMonth(), now.getDate(), time_parts[0], time_parts[1]);

            // add the interval and offset for next time to run report
            next_date = new Date(report_date.getTime() + interval + offset);

            // now set a timeout to run report and setInterval
            setTimeout(function () {
                rvbd.report.setSchedule();
            }, next_date - now);
        }

        rvbd.report.needs_reload_scheduled = false;
    },

    /**
     * Tell each Widget to refresh its content, used in auto-load reports
     */
    reloadAllWidgets: function () {
        rvbd.report.disableReloadButton();
        rvbd.report.disablePrintButton();

        if (rvbd.report.static) {
            rvbd.report.runFixedCriteriaReport();
        } else {
            $.each(rvbd.report.widgets, function (i, w) {
                w.reloadWidget()
            })
        }
    },

    /**
     * Called when user chooses new criteria through UI
     */
    criteriaChanged: function() {
        $('body').css('cursor', 'wait');

        rvbd.report.form = $('#criteria-form');
        rvbd.report.form.ajaxSubmit({
            dataType: 'json',
            type: 'post',
            url: rvbd.report.form.attr('action') + 'criteria/',
            complete: function(data, textStatus, jqXHR) {
                $('body').css('cursor', 'default');
            },
            success: function(data, textStatus) {
                rvbd.report.updateCriteria(data);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                if (jqXHR.status === 400) { // Form validation problems
                    $('#criteria').collapse('show');
                    $('#form-error-info').html(jqXHR.responseText);
                } else {
                    rvbd.report.alertReportError(textStatus, errorThrown);
                }
            }
        });
    },

    enablePrintButton: function() {
        $('<span id="print-report" class="glyphicon glyphicon-print enabled" href="#" title="Print this report"></span>')
             .click(rvbd.report.launchPrintWindow)
             .replaceAll('#print-report');
    },

    disablePrintButton: function() {
        $('<span id="print-report" class="glyphicon glyphicon-print disabled" title="Print this report (run report to enable)"></span>')
             .replaceAll('#print-report');
    },

    enableReloadButton: function() {
        $('<span id="reload-report" class="glyphicon glyphicon-refresh enabled" href="#" title="Reload all widgets in report"></span>')
            .click(rvbd.report.reloadAllWidgets)
            .replaceAll('#reload-report');
    },

    disableReloadButton: function() {
        $('<span id="reload-report" class="glyphicon glyphicon-refresh disabled" title="Reload all widgets in this report"></span>')
            .replaceAll('#reload-report');
    },

    /**
     * Starts execution of a standard form-based report; not used for embedded widgets or auto-run
     * reports. rvbd.report.doRunStandardReport() is triggered after the criteria box is fully collapsed.
     */
    runFormReport: function() {
        rvbd.report.runRequested = true;
        $("#criteria").collapse('hide'); // self.doRunReport() triggers on this element being hidden
    },

    /**
     * Performs the actual execution of a standard report (runFormReport updates the UI and then
     * runs this).
     */
    doRunFormReport: function(checkRunRequested) {
        if (typeof checkRunRequested === 'undefined' || checkRunRequested) {
            // Avoid accidental double clicks -- if this has already been executed since the last time
            // the user requested to run the report, abort.
            if (!rvbd.report.runRequested) {
                return;
            }

            rvbd.report.runRequested = false;
        }

        var $form = $('#criteria-form'),
            ajaxParams = {
                dataType: 'json',
                type: 'post',
                url: $form.attr('action'),
                complete: function(jqXHR, textStatus) {
                    $('body').css('cursor', 'default');
                },
                success: function(data, textStatus) {
                    rvbd.report.renderWidgets(data);
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    if (jqXHR.status === 400) {
                        $('#criteria').collapse('show');
                        $('#form-error-info').html(jqXHR.responseText);
                    } else {
                        rvbd.report.alertReportError(textStatus, errorThrown);
                    }
                }
            };

        if (typeof rvbd.report.printCriteria !== 'undefined') { // Print view
            ajaxParams.data = rvbd.report.printCriteria;
            $.ajax(ajaxParams);
        } else { // Standard form submit
            $form.ajaxSubmit(ajaxParams);
        }

        $('#id_debug').val(rvbd.report.debugFlag ? 'on' : '');
        $('#form-error-info').empty();
        $('body').css('cursor', 'wait');

        rvbd.report.debugFlag = false;
    },

    /**
     * Called to update criteria field HTML after the user chooses new criteria.
     */
    updateCriteria: function(data) {
        $.each(data, function(i, w) {
            $('#' + w.id + '-span').html(w.html);
        });
    },

    /**
     * Call to alert the user when we receive a server error from a report-wide
     * problem (e.g., invalid criteria).
     */
    alertReportError: function(textStatus, errorThrown) {
        alert("An error occurred: " + textStatus + ": " + errorThrown)
    },

    /**
     * Update the date/time header values
     */
    updateReportDateTime: function(datetime, timezone) {
        $('#report-datetime').html(datetime);
        $('#report-timezone').html(timezone);
    },

    /**
     * Renders all widgets in the current report (or just the one if this is an
     * embedded widget).
     */
    renderWidgets: function(definition) {
        var $report = $('#report'),
            reportMeta = definition.meta,
            widgets = definition.widgets,
            widgetsToRender;

        // lets store some data
        rvbd.report.meta = reportMeta;

        $('#id_debug').val(rvbd.report.debugFlag ? 'on' : '');
        rvbd.report.debug = reportMeta.debug;

        rvbd.report.updateReportDateTime(reportMeta.datetime, reportMeta.timezone);

        if (rvbd.report.needs_reload_scheduled == true) {
            rvbd.report.scheduleReloads(reportMeta.datetime);
        }

        $report.empty();

        if (!rvbd.report.isEmbedded) { // Full report
            widgetsToRender = widgets;
        } else { // Embedded widget
            // Find the widget we want to render
            var targetWidget;
            $.each(widgets, function(i, widget) {
                if (widget.widgetslug === rvbd.report.embedWidgetInfo.widgetslug) {
                    targetWidget = widget;
                    return false;
                }
            });

            // Replace the default criteria with the criteria from the widget request URL.
            $.extend(targetWidget.criteria, $.parseJSON(rvbd.report.embedWidgetInfo.criteria));

            widgetsToRender = [targetWidget];
        }

        // Clear existing list of widgets
        rvbd.report.widgets = [];

        var $row,
            rownum = 0,
            opts,
            widget;
        $.each(widgetsToRender, function(i, w) {
            if (w.row !== rownum) { // If we're at a new row number, create a new row element
                $row = $('<div></div>')
                    .addClass('row')
                    .addClass('sortable');  // mark contents as sortable
                rownum = w.row;
            }

            // Create empty div that the new widget object will populate
            var $div = $('<div></div>')
                .appendTo($row);
            $report.append($row);

            opts = w.options || {};
            opts.height = w.height;
            opts.width = w.width;
            opts.row = w.row;     // store for later
            opts.widgettype = w.widgettype;

            var widgetModule = w.widgettype[0],
                widgetClass = w.widgettype[1],
                urls = {"postUrl": w.posturl, "updateUrl": w.updateurl};

            widget = new rvbd.widgets[widgetModule][widgetClass](urls, rvbd.report.isEmbedded, $div[0],
                                                                 w.widgetid, w.widgetslug, opts, w.criteria, w.dataCache);
            rvbd.report.widgets.push(widget);
        });

        if (!rvbd.report.reportHasRendered) { // If first time rendering the report, attach widgetDoneLoading handler
            rvbd.report.reportHasRendered = true;

            $(document).on('widgetDoneLoading', function(e, widget_) {
                rvbd.report.handleReportLoadedIfNeeded(widget_);
            });
        }
    },

    /**
     * Check if all widgets are done loading, and if so, update the UI to indicate
     * the report is loaded.
     */
    handleReportLoadedIfNeeded: function(widget) {
        var widgetsRunning = false;

        $.each(rvbd.report.widgets, function(i, w) {
            if (w.status === 'running') {
                widgetsRunning = true;
            }
        });

        if (!widgetsRunning) {
            if (rvbd.report.debug) {
                rvbd.modal.alert("Download Zip File",
                                 "Complete - you will now be prompted to download a " +
                                 "zipfile containing the server logs.", "OK",
                                 function() { window.location = rvbd.report.debugUrl; });
            }

            // update datetime with meta from this last widget update
            // only updates from widget reloads
            if (widget.lastUpdate) {
                rvbd.report.updateReportDateTime(widget.lastUpdate.datetime,
                                                 widget.lastUpdate.timezone);
                rvbd.report.meta.lastUpdate = widget.lastUpdate;
            }

            // apply sortable to widgets
            $('.sortable').sortable({
                connectWith: ".sortable",
                handle: ".widget-title",
                cursor: "move"
            });

            rvbd.report.enablePrintButton();
            rvbd.report.enableReloadButton();

            //
            // setup and save state for history
            //
            var key = new Date().getTime();
            var saveobj = {
                meta: rvbd.report.meta,
                widgets: []
            };

            // re-create the definition objects for rendering and include
            // dataCache as the data we already retrieved for each widget
            $.each(rvbd.report.widgets, function(i, widget) {
                var w = {
                    posturl: widget.postUrl,
                    updateurl: widget.updateUrl,
                    widgettype: widget.options.widgettype,
                    widgetid: widget.id,
                    widgetslug: widget.slug,
                    options: widget.options,
                    height: widget.options.height,
                    width: widget.options.width,
                    criteria: widget.criteria,
                    row: widget.options.row,
                    dataCache: widget.dataCache
                };
                saveobj.widgets.push(w);
            });

            rvbd.report.saveState(key, saveobj);
        }
    }
};

})();
