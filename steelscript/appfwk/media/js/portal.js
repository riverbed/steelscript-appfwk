/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

// Shim for ES5 Object.create(). Ref: http://javascript.crockford.com/prototypal.html
if (typeof Object.create !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o;
        return new F();
    };
}

// Riverbed namespace object (used in all Riverbed JS files)
rvbd = {};

rvbd.modal = {
    html: function(heading, body, cancelButtonTxt, okButtonTxt, customClass) {
        if (typeof customClass === 'undefined') {
            customClass = '';
        }

        var modalHtml =
            '<div class="modal hide fade ' + customClass + '" id="test_id">' +
                '<div class="modal-header">' +
                    '<a class="close" data-dismiss="modal">&times;</a>' +
                    '<h3>' + heading +'</h3>' +
                '</div>' +
                '<div id="modalBody" class="modal-body"></div>';
        // if we don't include cancelButtonTxt then don't draw cancel button
        if( cancelButtonTxt ){
            modalHtml +=
                '<div class="modal-footer">' +
                    '<a href="#" id="cancelButton" class="btn" data-dismiss="modal">' +
                      cancelButtonTxt +
                    '</a>' +
                    '<a href="#" id="okButton" class="btn btn-primary">' +
                      okButtonTxt +
                    '</a>' +
                '</div>' +
              '</div>';
        }else{
            modalHtml +=
                '<div class="modal-footer">' +
                    '<a href="#" id="okButton" class="btn btn-primary">' +
                      okButtonTxt +
                    '</a>' +
                '</div>' +
              '</div>';
        }

        if (typeof body === 'string') {
            $body = $('<div></div>')
                .addClass('modal-content')
                .html(body);
        } else { // Assume DOM element
            $body = $(body);
        }

        $modal = $(modalHtml);
        $modal.find('#modalBody').append($body);

        return $modal;
    },

    // ref http://stackoverflow.com/a/10124151/2157429
    confirm: function(heading, question, cancelButtonTxt, okButtonTxt, okCallback, cancelCallback) {
        var modal = rvbd.modal.html(heading, question, cancelButtonTxt, okButtonTxt);

        modal.find('#okButton').click(function(event) {
          okCallback();
          modal.modal('hide');
        });

        if (typeof cancelCallback !== 'undefined') {
            modal.find('#cancelButton').click(function(event) {
              cancelCallback();
              modal.modal('hide');
            });        
        }


        modal.modal('show');
        modal.on('hidden', function() {
            $(this).remove();
        });
    },

    alert: function(heading, body, okButtonTxt, shownCallback, customClass) {
        var modal = rvbd.modal.html(heading, body, null, okButtonTxt, customClass);

        modal.find('#okButton').click(function(event) {
          modal.modal('hide');
          // return false to avoid the page scrolling to the top after click
          return false;
        });

        modal.on('shown', function(){
            shownCallback();
        });
        modal.on('hidden', function() {
            $(this).remove();
        });
        modal.modal('show');
    },

    form: function(heading, formHtml, formId, formHandlers, responseHandlers,
                   cancelButtonTxt, okButtonTxt, customClass) {
        // heading: text for modal header
        // formHtml: html of form, including '<form>' tags
        // formId: css id of form object in formHtml
        // formHandlers: object of selector->functions to be applied to modal
        // responseHandlers: object for handlers on ajax responses, available for
        //          'redirect', 'messages', 'form', 'error'
        // cancelButtonTxt:
        // okButtonTxt
        var modal = rvbd.modal.html(heading, formHtml, cancelButtonTxt, okButtonTxt, customClass);

        // need to destroy modal so handlers can be reapplied when next shown
        modal.on('hidden', function () {
            $(".modal").remove();
        });

        function applyHandlers() {
            formHandlers.forEach(function (elem, index, array) {
                modal.find('#' + formId).on(elem.event, elem.selector, elem.handler);
            });
        };

        modal.find('#okButton').click(function(event) {
            var form = $('#' + formId);
            form.ajaxSubmit({
                dataType: "json",
                type: form.attr('method'),
                url: form.attr('action'),
                success: function(data, textStatus) {
                    var json = $.parseJSON(data);
                    if (json.redirect) {
                        // successful post
                        if (responseHandlers.redirect) {
                            responseHandlers.redirect(json.redirect);
                        } else {
                            window.location.replace(json.redirect);
                        }
                    } else if (json.messages) {
                        // successful post - notification from processing
                        $('#messages').append(json.messages);
                        modal.modal('hide');
                    } else if (json.form) {
                        // error with post, updated form
                        form.replaceWith(json.form);
                        applyHandlers();
                    } else {
                        console.log('ERROR - unknown response from server: ' + json);
                    }
                }
            });
        });

        applyHandlers();

        modal.on('shown', function () {
            $('input:visible:first', this).focus();
        });

        modal.modal('show');
    },

    loading: function(heading, text) {
        var confirmModal =
          $('<div class="modal hide fade">' +
              '<div class="modal-header">' +
                '<h3>' + heading +'</h3>' +
              '</div>' +

              '<div class="modal-body">' +
                '<p class="text-center">' + text + '</p>' +
                '<p class="text-center">'  +
                   '<img src="/static/showLoading/images/loading.gif">' +
                '</p>' +
              '</div>' +

              '<div class="modal-footer">' +
                '&nbsp;' +
              '</div>' +
            '</div>');

        return confirmModal;
    },

    reloading: function(url, allReports) {
        if (allReports) {
            modal = rvbd.modal.loading('Reloading All Reports', 'Please wait ...');
        } else {
            modal = rvbd.modal.loading('Reloading Report', 'Please wait ...');
        }

        modal.modal('show');
        var next = window.location.href;
        window.location.href = url + "?next=" + next;
    },

    reloadRedirect: function(url, next) {
        // take explicit reload `url`, and explicit redirect `next` url
        var modal = rvbd.modal.loading('Reloading Report', 'Please wait ...');
        modal.modal('show');
        window.location.href = url + "?next=" + next;
    }
};
