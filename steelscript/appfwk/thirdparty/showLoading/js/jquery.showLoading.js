/*
 * jQuery showLoading plugin v1.0
 * 
 * Copyright (c) 2009 Jim Keller
 * Context - http://www.contextllc.com
 * 
 * Dual licensed under the MIT and GPL licenses.
 *
 * Modified by <cwhite@riverbed.com> to support displaying
 * percentage complete.
 */

(function($) {
'use strict';

$.fn.showLoading = function(options) {
    var $overlay = $('<div></div>')
            .attr('id', 'loading-indicator-' + $(this).attr('id') + '-overlay')
            .addClass('loading-indicator-overlay'),
        $indicator = $('<div></div>')
            .attr('id', 'loading-indicator-' + $(this).attr('id'))
            .addClass('loading-indicator');

    // If the position of the target element is set to "static," temporarily switch it to "relative"
    // so that it can act as a positioning context for the overlay.
    if ($(this).css('position') === 'static') {
        $(this).css('position', 'relative');
        $(this).data('wasStatic', true); // Remember that this element was static so we can flip it back later 
    } else {
        $(this).data('wasStatic', false);
    }

    // Add CSS class to hack in background opacity support for IE 8
    if (document.all && document.querySelector && !document.addEventListener) {
        overlay.addClass('ie8');
    }

    $overlay.append($indicator)
            .appendTo($(this));
        
    if (typeof options !== 'undefined' && typeof options.beforeShow !== 'undefined') {
        options.beforeShow($overlay, $indicator, this);
    }
    
    $overlay.show();

    return this;
};


$.fn.setLoading = function(pct) {
    $(this).find('.loading-indicator').html(String(pct) + "%");

    return this;
}


$.fn.hideLoading = function(options) {
    if ($(this).data('wasStatic')) {
        $(this).css('position', 'static');
    }

    $(this).find('.loading-indicator-overlay').remove();

    return this;
};

})(jQuery);