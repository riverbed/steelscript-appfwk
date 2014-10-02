/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */


function modal_html(heading, body, cancelButtonTxt, okButtonTxt, customClass) {
    if (typeof customClass === 'undefined') {
        customClass = '';
    }

    var modalHtml =
        '<div class="modal hide fade ' + customClass + '" id="test_id">' +
            '<div class="modal-header">' +
                '<a class="close" data-dismiss="modal">&times;</a>' +
                '<h3>' + heading +'</h3>' +
            '</div>' +

            '<div id="modalBody" class="modal-body">' +
                '<p>' + body + '</p>' +
            '</div>';
    // if we don't include cancelButtonTxt then don't draw cancel button
    if( cancelButtonTxt ){
        modalHtml +=
            '<div class="modal-footer">' +
                '<a href="#" class="btn" data-dismiss="modal">' +
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
    var confirmModal = $(modalHtml);
    return confirmModal;
}

// ref http://stackoverflow.com/a/10124151/2157429
function confirm(heading, question, cancelButtonTxt, okButtonTxt, callback) {
    var modal = modal_html(heading, question, cancelButtonTxt, okButtonTxt);

    modal.find('#okButton').click(function(event) {
      callback();
      modal.modal('hide');
    });

    modal.modal('show');
    modal.on('hidden', function() {
        $(this).remove();
    });
}

function alertModal(heading, body, okButtonTxt, shownCallback, customClass) {
    var modal = modal_html(heading, body, null, okButtonTxt, customClass);

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
}

function formModal(heading, form_html, form_id, form_handlers, response_handlers,
                   cancelButtonTxt, okButtonTxt, customClass) {
    // heading: text for modal header
    // form_html: html of form, including '<form>' tags
    // form_id: css id of form object in form_html
    // form_handlers: object of selector->functions to be applied to modal
    // response_handlers: object for handlers on ajax responses, available for
    //          'redirect', 'messages', 'form', 'error'
    // cancelButtonTxt:
    // okButtonTxt
    var modal = modal_html(heading, form_html, cancelButtonTxt, okButtonTxt, customClass);

    // need to destroy modal so handlers can be reapplied when next shown
    modal.on('hidden', function () {
        $(".modal").remove();
    });

    function apply_handlers() {
        form_handlers.forEach(function (elem, index, array) {
            modal.find('#' + form_id).on(elem.event, elem.selector, elem.handler);
        });
    };

    modal.find('#okButton').click(function(event) {
        var form = $('#' + form_id);
        form.ajaxSubmit({
            dataType: "json",
            type: form.attr('method'),
            url: form.attr('action'),
            success: function(data, textStatus) {
                var json = $.parseJSON(data);
                if (json.redirect) {
                    // successful post
                    if (response_handlers.redirect) {
                        response_handlers.redirect(json.redirect);
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
                    apply_handlers();
                } else {
                    console.log('ERROR - unknown response from server: ' + json);
                }
            }
        });
    });

    apply_handlers();

    modal.on('shown', function () {
        $('input:visible:first', this).focus();
    });

    modal.modal('show');
}

function loadingModal(heading, text) {

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
};

function reloadingModal(url, allReports) {
    if (allReports) {
        modal = loadingModal('Reloading All Reports', 'Please wait ...');
    } else {
        modal = loadingModal('Reloading Report', 'Please wait ...');
    }

    modal.modal('show');
    var next = window.location.href;
    window.location.href = url + "?next=" + next;
};

function reloadModalRedirect(url, next) {
    // take explicit reload `url`, and explicit redirect `next` url
    var modal = loadingModal('Reloading Report', 'Please wait ...');
    modal.modal('show');
    window.location.href = url + "?next=" + next;
};
