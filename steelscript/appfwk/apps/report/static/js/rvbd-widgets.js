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

/**
 * Utility funcs for formatting numbers and times. Called on every data point
 * in raw widget data to pre-format the values for the JS lib (or just to make
 * them look nicer to for the end user). Server-side code decides which of
 * these gets called to process the data for a given widget.
 */
rvbd.formatters = {
    padZeros: function(n, p) {
        var pad = (new Array(1 + p)).join("0");
        return (pad + n).slice(-pad.length);
    },

    roundAndPadRight: function(num, totalPlaces, precision) {
        var digits = Math.floor(num).toString().length;
        if (typeof precision === 'undefined') {
            if (digits >= totalPlaces) { // Always at least 1 digit of precision
                precision = 1;
            } else { // Include enough precision digits to get the total we want
                precision = (totalPlaces + 1) - digits; // One extra for decimal point
            }
        }
        return num.toFixed(precision);
    },

    formatTime: function(t, precision) {
        return (new Date(t)).toString();
    },

    formatDate: function(t, precision) {
        //t is epoch seconds in UTC time zone
        //Convert t to the date in UTC time zone
        var time = new Date(t);
        var year = time.getUTCFullYear();
        var month = time.getUTCMonth();
        var day = time.getUTCDate();
        return String(month+1) + "/" + String(day) + "/" + String(year);
    },

    formatTimeMs: function(t, precision) {
        var d = new Date(t);
        return d.getHours() +
            ':' + rvbd.formatters.padZeros(d.getMinutes(), 2) +
            ':' + rvbd.formatters.padZeros(d.getSeconds(), 2) +
            '.' + rvbd.formatters.padZeros(d.getMilliseconds(), 3);
     },

     formatMetric: function(num, precision) {
        if (typeof num === 'undefined') {
            return "";
        } else if (num === 0) {
            return "0";
        }

        num = Math.abs(num);

        var e = parseInt(Math.floor(Math.log(num) / Math.log(1000))),
            v = (num / Math.pow(1000, e));

        var vs = rvbd.formatters.roundAndPadRight(v, 4, precision);

        if (e >= 0) {
            return vs + ['', 'k', 'M', 'G', 'T'][e];
        } else {
            return vs + ['', 'm', 'u', 'n'][-e];
        }
    },

    formatIntegerMetric: function(num, precision) {
        return rvbd.formatters.formatMetric(num, 0);
    },

    formatPct: function(num, precision) {
        if (typeof num === 'undefined') {
            return "";
        } else if (num === 0) {
            return "0";
        } else {
            return rvbd.formatters.roundAndPadRight(num, 4, precision)
        }
    }
};

rvbd.widgets = {};

rvbd.widgets.Widget = function(urls, isEmbedded, div, id, slug, options, criteria, dataCache) {
    var self = this;

    self.postUrl = urls.postUrl;
    self.updateUrl = urls.updateUrl;
    self.div = div;
    self.id = id;
    self.slug = slug;
    self.options = options;
    self.criteria = criteria;

    if (dataCache) {
      self.dataCache = JSON.parse(dataCache);
    }

    self.status = 'running';
    self.asyncID = null;
    self.lastUpdate = {};     // object datetime/timezone of last update

    var $div = $(div);

    $div.attr('id', 'chart_' + id)
        .addClass('widget blackbox span' + (isEmbedded ? '12' : options.width))
        .text("Widget " + id);
    if (options.height) {
        $div.height(options.height);
    }

    $div.html("<p>Loading...</p>")
        .showLoading()
        .setLoading(0);

    if (!self.dataCache) {
      // If we are not using the cached report, follow normal
      // post request sequence
      self.postRequest(criteria);
    } else if (self.dataCache.status == 'error') {
      // No Widget Cache data exists
      self.displayError(self.dataCache);
      self.status = 'error';
    } else {
      // If we are using the cached report, load the data immediately
      $(self.div).hideLoading();
      self.render(self.dataCache);
      self.status = 'complete';
    }
};

rvbd.widgets.Widget.prototype = {

    postRequest: function(criteria) {
        var self = this;

        $.ajax({
            dataType: 'json',
            type: 'POST',
            url: self.postUrl,
            data: {criteria: JSON.stringify(criteria)},
            success: function (data, textStatus) {
                self.jobUrl = data.joburl;
                self.asyncID = setTimeout(function () {
                    self.getData(criteria);
                }, 1000);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                self.displayError(JSON.parse(jqXHR.responseText));
                self.status = 'error';
            }
        });
    },

    getData: function(criteria) {
        var self = this;

        $.ajax({
            dataType: "json",
            url: self.jobUrl,
            data: null,
            success: function(data, textStatus) {
                self.processResponse(criteria, data, textStatus);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                self.displayError(errorThrown);
            }
        });
    },

    processResponse: function(criteria, response, textStatus) {
        var self = this;

        switch (response.status) {
            case 3: // Complete
                $(self.div).hideLoading();
                self.render(response.data);
                self.status = 'complete';
                $(document).trigger('widgetDoneLoading', [self]);
                break;
            case 4: // Error
                self.displayError(response);
                self.status = 'error';
                $(document).trigger('widgetDoneLoading', [self]);
                break;
            default:
                $(self.div).setLoading(response.progress);
                self.asyncID = setTimeout(function() {
                    self.getData(criteria, self.processResponse);
                }, 1000);
        }
    },

    // Background Versions - post and query in the background without updates until done

    postRequestAsync: function(criteria) {
        var self = this;

        $.ajax({
            dataType: 'json',
            type: 'POST',
            url: self.postUrl,
            data: {criteria: JSON.stringify(criteria)},
            success: function (data, textStatus) {
                self.jobUrl = data.joburl;
                self.asyncID = setTimeout(function () {
                    self.getDataAsync(criteria);
                }, 1000);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                self.displayError(JSON.parse(jqXHR.responseText));
                self.status = 'error';
            }
        });
    },

    getDataAsync: function(criteria) {
        var self = this;

        $.ajax({
            dataType: "json",
            url: self.jobUrl,
            data: null,
            success: function(data, textStatus) {
                self.processResponseAsync(criteria, data, textStatus);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                self.displayError(errorThrown);
            }
        });
    },

    processResponseAsync: function(criteria, response, textStatus) {
        var self = this;

        switch (response.status) {
            case 3: // Complete, show spinner briefly then load data
                $(self.div).showLoading();
                setTimeout(function() {
                    self.processResponse(criteria, response, textStatus)
                }, 500);
                break;
            case 4: // Error
                self.processResponse(criteria, response, textStatus)
                break;
            default:
                self.asyncID = setTimeout(function() {
                    self.getDataAsync(criteria);
                }, 1000);
        }
    },

    reloadCriteria: function(callback) {
        // request updated criteria from server
        var self = this;

        $.ajax({
            dataType: 'json',
            type: 'GET',
            url: self.updateUrl,
            data: null,
            success: function (data, textStatus) {
                self.criteria = data.widgets[0].criteria;
                self.lastUpdate.datetime = data.meta.datetime;
                self.lastUpdate.timezone = data.meta.timezone;

                if (callback) {
                    callback();
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                self.displayError(JSON.parse(jqXHR.responseText));
                self.status = 'error';
            }
        });
    },

    cancelAsync: function() {
        var self = this;

        // cancel any pending async operations
        if (self.asyncID != null) {
            console.log('Cancelling async for id ' + self.asyncID);
            clearTimeout(self.asyncID);
            self.asyncID = null;
        }
    },

    reloadWidget: function() {
        // update whole widget with latest information
        var self = this;

        // avoid multiple request threads
        if (self.status == 'running') {
            self.cancelAsync();
        }

        self.status = 'running';

        self.reloadCriteria(
            function () {
                self.postRequestAsync(self.criteria);
            }
        );
    },

    /**
     *  Take the raw JSON object returned from the server and generate HTML to
     *  fill the widget DIV.
     */
    render: function(data) {
        var self = this;

        $(self.div).html(data);
    },

    /**
     * Returns a boolean indicating if the widget's content is too big for it
     * (i.e. it's scrolling). If so it will need to be enlarged in print view
     * if the user chooses "Expand Tables."
     */
    isOversized: function() {
        return false;
    },

    /**
     * Takes a JSON response object from a widget that failed with an error;
     * populates the widget with an error message based on the response.
     */
    displayError: function(response) {
        var self = this;

        var isException = (response.exception !== ''),
            $shortMessage = $('<span></span>').addClass('short-error-text'),
            $div = $(self.div);

        if (isException) { // Python exceptions are always text (encoded as HTML)
            $shortMessage.html(response.message);
        } else { // Non-exception errors sometimes contain HTML (double-encoded, e.g. <hr> becomes &lt;hr&gt;)
            $shortMessage.html($('<span></span>').html(response.message).text());
        }

        var $error = $('<div></div>')
            .addClass('widget-error')
            .append("Internal server error:<br>")
            .append($shortMessage)

        if (isException) {
            $error.append('<br>')
                  .append($('<a href="#">Details</a>')
                       .click(function() { self.launchTracebackDialog(response); }));
        }

        $div.hideLoading();

        $div.empty()
            .append($error);

        self.status = 'error';
    },

    launchTracebackDialog: function(response) {
        rvbd.modal.alert("Full Traceback", "<pre>" + $('<div></div>').text(response.exception).html() + "</pre>",
                         "OK", function() { }, 'widget-error-modal');
    },

    /**
     * Adds menu chevron to widget title bar
     */
    addMenu: function() {
        var self = this;
        var menuItems = [];

        // Don't include the embed option when already embedded!
        // or if not explicitly asked for
        if (!rvbd.report.isEmbedded && rvbd.report.embeddable_widgets) {
            menuItems.push('<a tabindex="-1" class="get-embed" href="#">Embed This Widget...</a>');
        }

        menuItems.push(
            '<a tabindex="0" id="' + self.id + '_export_widget_csv" class="export_widget_csv" href="#">Export CSV (Table Data)...</a>'
        );
        menuItems.push(
            '<a tabindex="1" id="' + self.id + '_show_criteria" class="show_criteria" href="#">Show Widget Criteria ...</a>'
        );

        var $menuContainer = $('<div></div>')
                .attr('id', 'reports-dropdown')
                .addClass('dropdown'),
            $menuButton = $('<a></a>')
                .attr('id', self.id + '_menu')
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
                    'aria-labelledby': self.id + '_menu'
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
                      .appendTo($(self.title));

        $menuContainer.find('.export_widget_csv').click($.proxy(self.onCsvExport, self));

        $(self.title).find('.get-embed').click($.proxy(self.embedModal, self));
        $(self.title).find('.show_criteria').click($.proxy(self.showCriteriaModal, self));
    },

    onCsvExport: function() {
        var self = this;

        $.ajax({
            dataType: 'json',
            type: 'POST',
            url: self.postUrl,
            data: { criteria: JSON.stringify(self.criteria) },
            success: function(data, textStatus, jqXHR) {
                self.checkCsvExportStatus(data.joburl);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                var alertBody = ("The server returned the following HTTP error: <pre>" +
                                 + errorThrown + '</pre>');
                rvbd.modal.alert("CSV Export Error", alertBody, "OK", function() { })
            }
        });
    },

    checkCsvExportStatus: function(csvJobUrl) {
        var self = this;

        $.ajax({
            dataType: "json",
            url: csvJobUrl + 'status/',
            data: null,
            success: function(data, textStatus) {
                switch (data.status) {
                    case 3: // Complete
                        var origin = window.location.protocol + '//' + window.location.host;
                        // remove spaces and special chars from widget title
                        var fname = self.titleMsg.replace(/\W/g, '');
                        // Should trigger file download
                        window.location = origin + '/jobs/' + data.id + '/data/csv/?filename=' + fname;
                        break;
                    case 4: // Error
                        var alertBody = ('The server returned the following error: <pre>' +
                                         data['message'] + '</pre>');
                        rvbd.modal.alert("CSV Export Error", alertBody, "OK", function() { });
                        break;
                    default: // Loading
                        setTimeout(function() { self.checkCsvExportStatus(csvJobUrl); }, 200);
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.log('Error when checking csv status');

                var alertBody = ('The server returned the following HTTP error: <pre>' + textStatus +
                                 ': ' + errorThrown + '</pre>');
                rvbd.modal.alert("CSV Export Error", alertBody, "OK", function() { });
            }
        });
    },


    /**
     * Construct this widget's basic layout--outer container, title bar, content
     * section. The subclasses are responsible for filling up the content section
     * with widget-specific content.
     */
    buildInnerLayout: function() {
        var self = this;

        var $div = $(self.div);

        self.outerContainer = $('<div></div>')
            .addClass('wid-outer-container')[0];

        self.title = $('<div></div>')
            .attr('id', $div.attr('id') + '_content-title')
            .html(self.titleMsg)
            .addClass('widget-title wid-title')
            .appendTo($(self.outerContainer))[0];

        self.content = $('<div></div>')
            .attr('id', $div.attr('id') + '_content')
            .addClass('wid-content')
            .appendTo($(self.outerContainer))[0];

        self.addMenu();

        $div.empty()
            .append(self.outerContainer);
    },

    /**
     * Display "embed widget" dialog for this widget.
     */
    embedModal: function() {
        var self = this;

        var urlCriteria = $.extend({}, self.criteria);

        // Delete starttime and endtime from params if present (we don't want embedded
        // widgets with fixed time frames)
        delete urlCriteria.starttime;
        delete urlCriteria.endtime;

        var widgetUrl = window.location.href.split('#')[0] + 'widgets/' + self.slug;

        //call server for auth token
        $.ajax({
            dataType: 'json',
            type: 'POST',
            url: widgetUrl + '/authtoken/',
            data: { criteria: JSON.stringify(urlCriteria) },
            success: function(data, textStatus) {
                   self.genEmbedWindow(widgetUrl, data.auth, urlCriteria, data.label_map);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                var alertBody = ("The server returned the following HTTP error: <pre>" +
                                 + errorThrown + '</pre>');
                rvbd.modal.alert("Auth Token Generation Error", alertBody, "OK", function() { })
            }
        });
    },

    genEmbedWindow: function(widgetUrl, token, criteria, label_map) {

        var self = this;
        var authUrl = widgetUrl + '/render/?auth=' + token;

        /* Generates the source code for the embed iframe */
        function genEmbedCode(url, width, height) {
            return '<iframe width="'+ width + '" height="' + height +
                   '" src="' + url + '" frameborder="0"></iframe>';
        };

        var div = '<div id="embed-modal" class="modal-content">' +
        '  Choose dimensions for the embedded widget:<br>' +
        '  <table>' +
        '  <tr>' +
        '     <th>Width:</th>' +
        '     <td><input value="500" type="text" id="embed-widget-width"></td>' +
        '  </tr>' +
        '  <tr>' +
        '      <th>Height:</th>' +
        '      <td><input value="312" type="text" id="embed-widget-height"></td>' +
        '  </tr>' +
        '  </table><br>' +
        '  Copy the following HTML to embed the widget:' +
        '  <input id="embed-widget-code" type="text">' +
        ' Choose criteria fields that can be overridden in the URL string:<br>' +
        ' <table id="criteriaTbl">';

        for (var field in criteria){
            if (criteria.hasOwnProperty(field) && label_map.hasOwnProperty(field)){
                div += '<tr>'+
                       '<th align="left">' + label_map[field] + '    ('+field + ')'+'</th>'+
                       '     <td><input type="checkbox" id="criteria-' + field + '"></td>' +
                       ' </tr>';
            }
        }
        div += ' </table><br>' +
               '</div>';

        $('body').append(div);


        var embedCode = genEmbedCode(authUrl, 500, self.options.height + 12);

        $('#embed-modal #embed-widget-code').attr('value', embedCode);

        function getEditFields() {
            var editFields = [];
            for (var field in criteria)
                if (criteria.hasOwnProperty(field))
                    if ($('#criteria-' + field).prop('checked'))
                        editFields.push(field);
            return editFields
        }

        function toggleEditField() {
             var editFieldsUrl = widgetUrl +'/' + token + '/editfields/';

             var dict = {edit_fields: getEditFields()};
            //call server for auth token
            $.ajax({
                dataType: 'json',
                type: 'POST',
                url: editFieldsUrl,
                //data: {dict: JSON.stringify(dict)},
                data: {edit_fields: JSON.stringify(getEditFields())},
                success: function(data, textStatus) {
                    updateIframe();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    var alertBody = ("The server returned the following HTTP error: <pre>" +
                                     + errorThrown + '</pre>');
                    rvbd.modal.alert("Add Edit Field Error", alertBody, "OK", function() { })
                }
            });
        }

        function updateIframe() {
            var tempUrl = authUrl;
            var fields = getEditFields();
            var fieldsObj = {}
            for (var index in fields)
                fieldsObj[fields[index]] = criteria[fields[index]]

            tempUrl += '&' + $.param(fieldsObj)
            $('#embed-modal #embed-widget-code').attr('value',
                genEmbedCode(tempUrl, $('#embed-widget-width').val(),
                                      $('#embed-widget-height').val()));
        };

        rvbd.modal.alert("Embed Widget HTML", $('#embed-modal')[0], "OK", function() {
            // automatically focus and select the embed code
            $('#embed-widget-code')
                .on('mouseup focus', function() { this.select(); })
                .focus();

            // update the embed code to reflect the width and height fields
            $('#embed-widget-width, #embed-widget-height').keyup(updateIframe);
            // update the embed code to reflect the checked criteria fields
            $('#criteriaTbl').click(toggleEditField);
        });
    },

    /**
     * Display dialog with widget's criteria
     */
    showCriteriaModal: function() {
        var self = this;
        var body = $('<pre></pre>').html(JSON.stringify(self.criteria, null, 2));
        var title = self.titleMsg + ' Criteria';

        rvbd.modal.alert(title, body, "OK", function() { })
    },
};

rvbd.widgets.raw = {};

rvbd.widgets.raw.TableWidget = function(postUrl, isEmbedded, div, id, slug, options, criteria, dataCache) {
    rvbd.widgets.Widget.apply(this, [postUrl, isEmbedded, div, id, slug, options, criteria, dataCache]);
};
rvbd.widgets.raw.TableWidget.prototype = Object.create(rvbd.widgets.Widget.prototype);

rvbd.widgets.raw.TableWidget.prototype.render = function(data) {
    var self = this;

    var $table = $('<table></table>')
                     .attr('id', $(self.div).attr('id') + "_content")
                     .width('100%'),
        $tr;

    $.each(data, function(i, row) {
        $tr = $('<tr></tr>');
        $.each(row, function(i, col) {
            $tr.append('<td></td>').html(col);
        });
        $table.append($tr);
    });

    $(self.div).empty().append($table);
};

/* Use this with the Column.formatter as follows:

     table.add_column('col', datatype='string',
                      formatter='rvbd.formatHealth')

   The valid table column values are defined in report.css:
      green, yellow, red, yellow
   yielding "green-circle" as a class.
*/

rvbd.formatHealth = function(v) {
    return '<div class="' + v + '-circle"></div>';
};

/*
To create a colored circle with optional text and a tooltip
*/
rvbd.formatHealthWithHover = function(v) {
/*
    Argument v is a ':' separated concatenation of 3 strings s1:s2:s3 where:

    s1 is the color of the circle and is one of 'red','green','yellow','grey'.
    s2 is a text that will appear next to the circle.
    s3 is a text that will appear as a tooltip when hovering the mouse over the s1 circle.

    A single string without ':' is treated as s1 only (no text no tooltip).
    A string with only one ':' is treated as s1:s2 (no tooltip).
    A s1::s3 string is a valid way of having a tooltip but no text.
*/

    var arr = v.split(':');
    var color = arr[0];

    var visible_text = '';
    var tooltip_text = '';

    if (arr.length > 1 && arr[1] != '') {
        visible_text = '<div class="info">' + arr[1] + '</div>';
    }

    if (arr.length > 2 && arr[2] != '') {
        tooltip_text = '<div class="tooltiptext">' + arr[2] + '</div>';
    }

    return '<div class="' + color + '-circle wide">' + tooltip_text + visible_text + '</div>'
};



})();
