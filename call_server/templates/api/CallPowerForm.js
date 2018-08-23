/*!
  * CallPowerForm.js
  * Connects embedded action form to CallPower campaign
  * Requires jQuery >= 1.7.0
  *    proxy (1.4), deferred (1.5), promises (1.6), on (1.7)
  *
  * Displays call script in overlay or by replacing form
  * Override functions onSuccess or onError in CallPowerOptions
  * Instantiate with form selector to connect callbacks
  * (c) Spacedog.xyz 2015, license AGPLv3
  */

// revealing module pattern
var CallPowerForm = function (formSelector, $) {
  // instance variables
  this.$ = $;  // stash loaded version of jQuery, in case there are conflicts with window
  this.form = this.$(formSelector);
  {% if campaign.embed %}
  this.locationField = this.$('{{campaign.embed.get("location_sel","#location_id")}}');
  this.phoneField = this.$('{{campaign.embed.get("phone_sel","#phone_id")}}');
  {% else %}
  this.locationField = this.$("#location_id");
  this.phoneField = this.$("#phone_id");
  {% endif %}
  this.locateBy = '{{campaign.locate_by}}';
  this.scriptDisplay = 'overlay';
  
  // allow options to override settings
  for (var option in window.CallPowerOptions || []) {
    var setting = CallPowerOptions[option];
    // accept jquery selectors for form and fields
    var selectorFields = ['form', 'locationField', 'phoneField'];
    if ($.inArray(option, selectorFields) != -1 && typeof setting === 'string') {
      this[option] = this.$(setting);
    } else { 
      this[option] = setting;
    }
  }

  // bind our submit event to makeCall
  this.form.on("submit.CallPower", this.$.proxy(this.makeCall, this));
  // include custom css
  if(this.customCSS !== undefined) {
    var link_elem = 'link rel="stylesheet" href="';
    // one weird trick to create the element without it rendering in browsers
    this.$('head').append('<'+link_elem+this.customCSS+'" />');
  }
};

CallPowerForm.prototype = function() {
  // prototype variables
  var createCallURL = '{{url_for("call.create", _external=True)}}';
  var campaignId = "{{campaign.id}}";

  var simpleGetCountry = function() {
    return "{{campaign.country_code|default('US')}}";
  };

  var cleanUSZipcode = function(val) {
    if (val.length === 0) { return undefined; }
    var isValid = /(\d{5}([\-]\d{4})?)/.test(val);
    return isValid ? val : false;
  };

  var cleanCAPostal = function(val) {
      if (val === 0) { return undefined; }
      var valNospace = val.replace(/\W+/g, '');
      var isValid = /([ABCEGHJKLMNPRSTVXY]\d)([ABCEGHJKLMNPRSTVWXYZ]\d){2}/i.test(valNospace);
      return isValid ? valNospace : false;
  };

  // very simple country specific validators
  // override with eg google places autocomplete
  var simpleValidateLocation = function() {
    countryCode = this.country();

    if (this.locationField.length == 1) {
      var locationVal = this.locationField.val();
    } else {
      var locationVal = '';
      this.locationField.each(function() { 
        locationVal += (' ' + $(this).val());
      });
      locationVal = locationVal.trim();
    }

    if (this.locateBy === 'postal') {
      if (countryCode === 'US') { return cleanUSZipcode(locationVal); }
      else if (countryCode === 'CA') { return cleanCAPostal(locationVal); }
    }
    return locationVal;
  };

  // very simple country specific length validators
  // override with eg: google libphonenumber
  var simpleValidatePhone = function(countryCode) {
    countryCode = this.country();

    if (this.phoneField.length === 0) { return undefined; }
    // remove whitespace, parents, plus, dashes from phoneField
    var num = this.phoneField.val()
      .replace(/\s/g, '').replace(/\(/g, '').replace(/\)/g, '')
      .replace('+', '').replace(/\-/g, '');
    return num;

    var isValid = false;
    var prefix;
    if (countryCode === 'US' || countryCode === 'CA') {
        prefix = "1";
        // strip leading prefix
        if (num.charAt(0) === prefix) {
          num = num.substr(1);
        }
        isValid = (num.length == 10); // ensure just 10 digits remain
    }
    else if (countryCode === 'GB') {
        prefix = "44";
        // strip leading prefix
        if (num.slice(0,2) === prefix) {
          num = num.substr(2);
        }
        isValid = (num.length >= 9); // ensure at least 9 digits remain 
    }
    else {
      prefix = '';
      isValid = (num.length > 8); // ensure at least a few digits remain
    }

    // re-append prefix and plus sign, for e164 dialing
    if (prefix || prefix === '') {
      num = "+"+prefix+num;
    }
    return isValid ?  num : false;
  };


  var onSuccess = function(response) {
    if (response.campaign === 'archived') { return onError(this.form, 'This campaign is no longer active.'); }
    if (response.campaign !== 'live') { return onError(this.form, 'This campaign is not active.'); }
    if (response.call !== 'queued') { return onError(this.form, 'Could not start call.'); }
    if (response.script === undefined) { return false; }

    if (this.phoneDisplay) {
      $(this.phoneDisplay).html(response.fromNumber);
    }

    if (this.scriptDisplay === 'overlay') {
      // display simple overlay with script content
      var scriptOverlay = this.$('<div class="overlay"><div class="modal">'+response.script+'</div></div>');
      this.$('body').append(scriptOverlay);
      scriptOverlay.overlay();
      scriptOverlay.css('visibility', 'visible');
      scriptOverlay.addClass('shown');
    }

    if (this.scriptDisplay === 'replace') {
      // hide form and show script contents

      // start new empty hidden div
      var scriptDiv = this.$('<div style="display: none;"></div>');
      // copy existing form classes and styling
      scriptDiv.addClass(this.form.attr('class'));
      // insert response contents
      scriptDiv.html(response.script);

      scriptDiv.insertAfter(this.form);
      this.form.slideToggle();
      scriptDiv.slideToggle();
    }

    if (this.scriptDisplay === 'redirect') {
      // save response url to redirect after original form callback
      this.redirectAfter = response.redirect;
    }

    if (this.scriptDisplay === 'alert') {
      // popup alert with response.script text
      var message = this.$(response.script);
      alert(message.text());
    }

    // run custom js function
    if(typeof this.customJS !== 'undefined') {
      var $ = this.$; // make our version of jQuery available to local context
      if(typeof this.customJS === 'string' ) { eval(this.customJS); }
      else if (typeof this.customJS === 'function') { this.customJS(); }
    }

    return true;
  };

  var onError = function(element, message) {
    if (element !== undefined) {
      element.addClass('has-error');  
    } else {
      console.error(message);  
    }
    return false;
  };

  var makeCall = function(event, options) {
    // stop default form submit event
    if (event !== undefined) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }

    if (this.locationField.length && !this.location()) {
      return this.onError(this.locationField, 'Invalid location');
    }
    if (this.phoneField.length && !this.phone()) {
      return this.onError(this.phoneField, 'Invalid phone number');
    }

    this.$.ajax(createCallURL, {
      method: 'GET',
      data: {
        campaignId: campaignId,
        userLocation: this.location(),
        userPhone: this.phone(),
        userCountry: this.country()
      }
    })
    .done(this.$.proxy(this.onSuccess, this))
    .fail(this.$.proxy(this.onError, this, this.form, 'Please fill out the form completely'))
    .then(this.$.proxy(function() {
      // turn off our submit event
      this.form.off('submit.CallPower');

      // redirect after original form submission is complete
      
      if (this.scriptDisplay === 'overlay') {
        var scriptOverlay = this.$('.overlay');
        // bind overlay hide to original form submit
        scriptOverlay.on('hide', this.$.proxy(this.formSubmit, this));
        scriptOverlay.on('click', this.$.proxy(function(e) {
          if (e.target.className === scriptOverlay.attr('class')) return scriptOverlay.trigger('hide');
          // only trigger hide when clicking overlay background, not modal
        }, this));
      } else if (this.scriptDisplay === 'replace') {
        // original form still exists, but is hidden
        // do nothing
      } else if (this.scriptDisplay === 'redirect' && this.redirectAfter) {
          window.location.replace(this.redirectAfter);
      } else {
        // re-trigger original form submit
        this.formSubmit();
      }
    }, this))
    .fail(this.$.proxy(this.onError, this, this.form, 'Sorry, there was an error making the call'));

    return false;
    // just in case, to stop initial event propagation
  };

  var formSubmit = function() {
    // trigger form submit event after optional delay
    window.setTimeout(this.$.proxy(function() { this.form.trigger('submit'); }, this), this.submitDelay || 0);
  };

  // public method interface
  var public = {
    getCountry: simpleGetCountry,
    getLocation: simpleValidateLocation,
    getPhone: simpleValidatePhone,
    onError: onError,
    onSuccess: onSuccess,
    makeCall: makeCall,
    formSubmit: formSubmit
  };
  // let these be overridden, but keep reference to original functions
  public.country = public.getCountry;
  public.location = public.getLocation;
  public.phone = public.getPhone;
  return public;
} ();
