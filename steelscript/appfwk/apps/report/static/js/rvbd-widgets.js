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

if (typeof Object.create !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o;
        return new F();
    };
}


window.Widget = function(posturl, divid, options, criteria) {
    var self = this;

    self.options = options;
    self.posturl = posturl;
    self.div = document.getElementById(divid);

    var $div = $(self.div);

    if (options.height) {
        $div.height(options.height);
    }

    $div.html("<p>Loading...</p>")
        .showLoading()
        .setLoading(0);

    $.ajax({
        dataType: 'json',
        type: 'POST',
        url: self.posturl,
        data: { criteria: JSON.stringify(criteria) },
        success: function(data, textStatus) {
            self.joburl = data.joburl;
            setTimeout(function() { self.getData(criteria); }, 1000);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            var message = $("<div/>").html(textStatus + " : " + errorThrown).text()
            $div.hideLoading()
                .append("<p>Server error: <pre>" + message + "</pre></p>");
            window.rvbd_status[self.posturl] = 'error';
        }
    });
}

window.Widget.prototype = {
    getData: function(criteria) {
        var self = this;

        $.ajax({
            dataType: "json",
            url: self.joburl,
            data: null,
            success: function(data, textStatus) {
                self.processResponse(criteria, data, textStatus);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                self.displayError(response);
            }
        });
    },

    processResponse: function(criteria, response, textStatus) {
        var self = this;

        switch (response.status) {
            case 3: // COMPLETE
                $(self.div).hideLoading();
                self.render(response.data);
                window.rvbd_status[self.posturl] = 'complete';
                break;
            case 4: // ERROR
                self.displayError(response);
                break;
            default:
                $(self.div).setLoading(response.progress);

                setTimeout(function() { self.getData(criteria); }, 1000);
        }
    },

    render: function(data) {
        var self = this;

        $(self.div).html(data);
    },

    roundAndPadRight: function(num, totalPlaces, precision) {
        var digits = Math.floor(num).toString().length;
        if (typeof precision === 'undefined') {
           if (digits >= totalPlaces) { // Always at least 1 digit of precision
               var precision = 1;
           } else { // Include enough precision digits to get the total we want
               var precision = (totalPlaces + 1) - digits; // One extra for decimal point
           }
        }
        return num.toFixed(precision);
    },

    formatTime: function(t, precision) {
        return (new Date(t)).toString();
    },

    padZeros: function(n, p) {
        var pad = (new Array(1 + p)).join("0");
        return (pad + n).slice(-pad.length);
    },

    formatTimeMs: function(t, precision) {
        var self = window.Widget.prototype;
        var d = new Date(t);
        return d.getHours() +
            ':' + self.padZeros(d.getMinutes(), 2) +
            ':' + self.padZeros(d.getSeconds(), 2) +
            '.' + self.padZeros(d.getMilliseconds(), 3);
        // return date.toString();
     },

     formatMetric: function(num, precision) {
        var self = this;

        if (typeof num === 'undefined') {
            return "";
        } else if (num === 0) {
            return "0";
        }

        num = Math.abs(num);

        var e = parseInt(Math.floor(Math.log(num) / Math.log(1000))),
            v = (num / Math.pow(1000, e));

        var vs = self.roundAndPadRight(v, 4, precision);

        if (e >= 0) {
            return vs + ['', 'k', 'M', 'G', 'T'][e];
        } else {
            return vs + ['', 'm', 'u', 'n'][-e];
        }
    },

    formatIntegerMetric: function(num, precision) {
        var self = this;

        return self.formatMetric(num, 0);
    },

    formatPct: function(num, precision) {
        var self = this;

        if (typeof num === 'undefined') {
            return "";
        } else if (num === 0) {
            return "0";
        } else {
            return self.roundAndPadRight(num, 4, precision)
        }
    },

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
            .append("Internal server error: ")
            .append('<br/>')
            .append($shortMessage)

        if (isException) {
            $error.append('<br/>')
                  .append($('<a href="#">Details</a>')
                       .click(function() { self.launchTracebackDialog(response); }));
        }

        $div.hideLoading();

        $div.empty()
            .append($error);

        window.rvbd_status[self.posturl] = 'error';
    },

    launchTracebackDialog: function(response) {
        alertModal("Full Traceback", "<pre>" + $('<div></div>').text(response.exception).html() + "</pre>",
                   "OK", function() { }, 'widget-error-modal');
    }
}

window.rvbd_raw = {};

window.rvbd_raw.TableWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
};
window.rvbd_raw.TableWidget.prototype = Object.create(window.Widget.prototype);

window.rvbd_raw.TableWidget.prototype.render = function(data) {
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
}

})();
