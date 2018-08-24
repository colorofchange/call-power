{% include "api/CallPowerForm.js" with context %}

var main = function($) {
  {% if campaign.embed %}
    callPowerForm = new CallPowerForm('{{campaign.embed.get("form_sel","#call_form")}}', $);
    {% if campaign.embed.get('script_display') == 'overlay' %}
      $.getScript("{{ url_for('static', filename='embed/overlay.js', _external=True) }}");
      $('head').append('<link rel="stylesheet" href="{{ url_for("static", filename="embed/overlay.css", _external=True) }}" />');
    {% endif %}
    {% if campaign.embed.get('custom_onload') %}
      /* the following comes from campaign {{campaign.id}}'s custom_onload script */
      {{campaign.embed.get('custom_onload')}}
      /* end custom */
    {% endif %}
  {% else %}
    {# if embed not defined, try to attach to the first form we see #}
    callPowerForm = new CallPowerForm('form', $);
  {% endif %}
  {# check javascript context also, in case script display is defined in templates but not this campaign #}
  if (window.CallPowerOptions && window.CallPowerOptions.scriptDisplay === 'overlay' && !$.overlay) {
    $.getScript("{{ url_for('static', filename='embed/overlay.js', _external=True) }}");
    $('head').append('<link rel="stylesheet" href="{{ url_for("static", filename="embed/overlay.css", _external=True) }}" />');
  }
}

// from substack/semver-compare
// license MIT
function versionCmp (a, b) {
    var pa = a.split('.');
    var pb = b.split('.');
    for (var i = 0; i < 3; i++) {
        var na = Number(pa[i]);
        var nb = Number(pb[i]);
        if (na > nb) return 1;
        if (nb > na) return -1;
        if (!isNaN(na) && isNaN(nb)) return 1;
        if (isNaN(na) && !isNaN(nb)) return -1;
    }
    return 0;
};

// from https://css-tricks.com/snippets/jquery/load-jquery-only-if-not-present/
function getScript(url, success, cors) {
    var script = document.createElement('script');
    script.src = url;
    if (cors) {
      script.crossOrigin = cors;
    }

    var head = document.getElementsByTagName('head')[0],
    done = false;
    
    // Attach handlers for all browsers
    script.onload = script.onreadystatechange = function() {
      if (!done && (!this.readyState || this.readyState == 'loaded' || this.readyState == 'complete')) {
      
      done = true;
      // callback function provided as param
      success();
      script.onload = script.onreadystatechange = null;
      head.removeChild(script);
    };
  };  
  head.appendChild(script);
};

if (typeof window.jQuery === 'undefined') {
  // load jQuery from cloudflare
  getScript('//cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.js', function() {
    return main(jQuery);
  });
} else if (versionCmp(window.jQuery.fn.jquery, '1.7.0') < 0) {
  console.log('jQuery is really old', jQuery.fn.jquery);
  getScript('//cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js', function() {
    // make sure new version of jQuery plays nice with existing one
    jQuery.noConflict();
    return main(jQuery);
  });
} else {
  // in-page jQuery is sufficient, carry on
  jQuery(document).ready(main);
}

// load sentry for frontend error tracking
if (window.CallPowerOptions.errorTracking) {
  getScript('https://cdn.ravenjs.com/3.22.1/raven.min.js',
    function() {
      Raven.config('{{DSN_PUBLIC}}').install();
    },
    'anonymous')
}
