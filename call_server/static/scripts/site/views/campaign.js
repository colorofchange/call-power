/*global CallPower, Backbone */

(function () {
  CallPower.Views.CampaignForm = Backbone.View.extend({
    el: $('form#campaign'),

    events: {
      // generic
      'click a.clear': 'clearRadioChoices',

      // campaign targets
      'change select#campaign_country':  'changeCampaignCountry',
      'change select#campaign_type':  'changeCampaignType',
      'change select#campaign_subtype':  'changeCampaignSubtype',
      'change input[name="segment_by"]': 'changeSegmentBy',

      // include special
      'change input[name="show_special"]': 'showSpecial',
      'change select[name="include_special"]': 'changeIncludeSpecial',

      // call limits
      'change input[name="call_limit"]': 'changeCallLimit',

      // phone numbers
      'change select#phone_number_set': 'checkForCallInCollisions',
      'change input#allow_call_in': 'checkForCallInCollisions',

      'submit': 'submitForm'
    },

    initialize: function() {
      // init child views

      this.searchForm = new CallPower.Views.TargetSearch();
      this.targetListView = new CallPower.Views.TargetList();

      // clear nested choices until updated by client
      if (!$('select.nested').val()) { $('select.nested').empty(); }

      // trigger change to targeting fields
      // so defaults show properly
      this.changeCampaignCountry();
      this.changeCampaignType();
      this.changeSegmentBy();
      this.changeIncludeSpecial();

      if ($('input[name="call_maximum"]').val()) {
        $('input[name="call_limit"]').attr('checked', 'checked');
      }

      // load existing items from hidden inputs
      this.targetListView.loadExistingItems();

      $("#phone_number_set").parents(".controls").after(
        $('<div id="call_in_collisions" class="alert alert-warning col-sm-4 hidden">').append(
          "<p>This will override call in settings for these campaigns:</p>",
          $("<ul>")
        )
      );

      this.checkForCallInCollisions();
    },

    changeCampaignCountry: function() {
      if ($('select#campaign_country').attr('disabled')) {
        // country already set, no need to update type
        return false;
      }

      // updates campaign_type with available choices from data-attr
      var country = $('select#campaign_country').val();
      var nested_field = $('select#campaign_type');
      var nested_val = nested_field.val();

      var type_choices = nested_field.data('nested-choices');
      var selected_choices = type_choices[country];
      
      // clear existing choices
      nested_field.empty();
      nested_field.append('<option val=""></option>');

      // append new ones
      $(selected_choices).each(function() {
        var option = $('<option value="'+this[0]+'">'+this[1]+'</option>');
        if (option.val() === nested_val) { option.attr('selected', true); }
        nested_field.append(option);
      });
    },

    changeCampaignType: function() {
      // show/hide target segmenting based on campaign country and type
      var country = $('select#campaign_country').val();
      var type = $('select#campaign_type').val();

      if (country ==='us') {
        if (type === "congress") {
          // hide campaign_state form-group
          $('.form-group.campaign_state').hide();
        }

        // local or custom: no segment, location or search, show custom target_set
        if (type === "custom" || type === "local" || type === "executive") {
          // set default values
          $('.form-group.locate_by input[name="locate_by"][value=""]').click();
          $('.form-group.segment_by input[name="segment_by"][value="custom"]').click();
          // hide fields
          $('.form-group.segment_by').hide();
          $('.form-group.locate_by').hide();
          $('#target-search').hide();
          // show custom target search
          $('#set-targets').show();
          // hide target_offices
          $('.form-group.target_offices').hide();
        } else {
          // legislative, show segmenting and search
          $('.form-group.segment_by').show();
          $('.form-group.locate_by').show();
          $('.form-group.target_offices').show();
          $('#target-search').show();

          var segment_by = $('input[name="segment_by"]:checked');
          // unless segment_by is custom
          if (segment_by.val() !== 'custom') {
            $('#set-targets').hide();
          }
        }
      }

      this.changeCampaignSubtype();
    },

    changeCampaignSubtype: function(event) {
      var country = $('select#campaign_country').val();
      var type = $('select#campaign_type').val();
      var subtype = $('select#campaign_subtype').val();

      // show all search fields
      $('.search-field ul.dropdown-menu li a').show();

      if (country === 'us') {
        $('.search-field ul.dropdown-menu li #state').text('State');

        if (type === 'state') {
          if (subtype === 'exec') {
            $('#target-search input[name="target-search"]').attr('placeholder', 'search US Governors');
          } else {
            $('#target-search input[name="target-search"]').attr('placeholder', 'search OpenStates');
            $('.search-field ul.dropdown-menu li #state').hide(); // already searching by state
          }
        }

        // congress: show/hide target_ordering values upper_first and lower_first
        if ((type === 'congress' && subtype === 'both') ||
            (type === 'state' && subtype === 'both')) {
          $('input[name="target_ordering"][value="upper-first"]').parent('label').show();
          $('input[name="target_ordering"][value="lower-first"]').parent('label').show();
        } else {
          $('input[name="target_ordering"][value="upper-first"]').parent('label').hide();
          $('input[name="target_ordering"][value="lower-first"]').parent('label').hide();
        }
      }

      if (country === 'ca') {
        $('.search-field ul.dropdown-menu li #state').text('Province');
        $('#target-search input[name="target-search"]').attr('placeholder', 'search OpenNorth');

        if (type === 'province') {
          $('.search-field ul.dropdown-menu li #state').hide(); // already searching by province
        }
      }
    },

    clearRadioChoices: function(event) {
      var buttons = $(event.target).parent().find('input[type="radio"]');
      buttons.attr('checked',false).trigger('change'); //TODO, debounce this?
    },

    changeSegmentBy: function() {
      var segment_by = $('input[name="segment_by"]:checked').val();

      if (segment_by === 'location') {
        $('.form-group.locate_by').show();

        // target_ordering can be chamber dependent
        $('input[name="target_ordering"][value="upper-first"]').parent('label').show();
        $('input[name="target_ordering"][value="lower-first"]').parent('label').show();

        // target_offices can use districts
        $('.form-group.target_offices').show();
      } else {
        $('.form-group.locate_by').hide();

        // target_ordering can only be 'in order' or 'shuffle'
        $('input[name="target_ordering"][value="upper-first"]').parent('label').hide();
        $('input[name="target_ordering"][value="lower-first"]').parent('label').hide();

        // target_offices will be default
        $('.form-group.target_offices').hide();
      }

      if (segment_by === 'custom') {
        $('#set-targets').show();
        $('.form-group.special_targets').hide();
      } else {
        $('#set-targets').hide();
        $('.form-group.special_targets').show();
        this.showSpecial();
      }
    },

    showSpecial: function(event) {
      var specialGroup = $('select[name="include_special"]').parents('.input-group');
      if ($('input[name="show_special"]').prop('checked')) {
        specialGroup.show();
        $('#set-targets').show();
      } else {
        specialGroup.hide();
        $('#set-targets').hide();
        $('select[name="include_special"]').val('').trigger('change');
      }
    },

    changeIncludeSpecial: function() {
      var include_special = $('select[name="include_special"]').val();

      if (include_special === 'only') {
        // target_ordering can only be 'in order' or 'shuffle'
        $('input[name="target_ordering"][value="upper-first"]').parent('label').hide();
        $('input[name="target_ordering"][value="lower-first"]').parent('label').hide();
      } else {
        // target_ordering can be chamber dependent
        $('input[name="target_ordering"][value="upper-first"]').parent('label').show();
        $('input[name="target_ordering"][value="lower-first"]').parent('label').show();
      }
    },

    changeCallLimit: function(event) {
      var callMaxGroup = $('input[name="call_maximum"]').parents('.form-group');
      if ($(event.target).prop('checked')) {
        callMaxGroup.show();
      } else {
        callMaxGroup.hide();
        $('input[name="call_maximum"]').val('');
      }
    },

    checkForCallInCollisions: function(event) {
      var collisions = [];
      var taken = $("select#phone_number_set").data("call_in_map");
      $("select#phone_number_set option:selected").each(function() {
        if (taken[this.value] && collisions.indexOf(taken[this.value]) == -1)
          collisions.push(taken[this.value]);
      });

      var list = $("#call_in_collisions ul").empty();
      list.append($.map(collisions, function(name) { return $("<li>").text(name) }));

      if ($("#allow_call_in").is(":checked") && collisions.length)
        $("#call_in_collisions").removeClass("hidden");
      else
        $("#call_in_collisions").addClass("hidden");
    },

    validateNestedSelect: function(formGroup) {
      if ($('select.nested:visible').length) {
        return !!$('select.nested option:selected').val();
      } else {
        return true;
      }
    },

    validateState: function(formGroup) {
      var campaignType = $('select#campaign_type').val();
      var campaignSubtype = $('select#campaign_subtype').val();
      if (campaignType === "state") {
        if (campaignSubtype === "exec") {
          // governor campaigns can cross states
          return true;
        } else {
          // other types require a state to be selected
          return !!$('select[name="campaign_state"] option:selected').val();
        }
      } else {
        return true;
      }
    },

    validateSegmentBy: function(formGroup) {
      // if campaignType is custom or local, set segmentBy to custom and uncheck locate_by
      var campaignType = $('select#campaign_type').val();
      if (campaignType === "custom" || campaignType === "local") {
        $('input[name="segment_by"][value="custom"]').click();
        $('input[name="locate_by"]').attr('checked', false);
      }
      return true;
    },

    validateLocateBy: function(formGroup) {
      // if segmentBy is location, locateBy must have value
      var segmentBy = $('input[name="segment_by"]:checked').val();
      if (segmentBy === "location") {
        return !!$('input[name="locate_by"]:checked').val();
      } else {
        return true;
      }
    },

    validateTargetList: function(f) {
      // if type == custom, ensure we have targets
      if ($('select#campaign_type').val() === "custom") {
        return !!CallPower.campaignForm.targetListView.collection.length;
      } else {
        return true;
      }
    },

    validateSpecialTargets: function(f) {
      // if show_special checked, ensure we also have include_special set
      if ($('input#show_special:checked').val()) {
        return !!$('select#include_special').val();
      } else {
        return true;
      }
    },

    validateSelected: function(formGroup) {
      return !!$('select option:selected', formGroup).length;
    },

    validateField: function(formGroup, validator, message) {
      // first check to see if formGroup is present
      if (!formGroup.length) {
        return true;
      }

      // run validator for formGroup
      var isValid = validator(formGroup);

      // put message in last help-block
      if (!isValid) {
        $('.help-block', formGroup).last().text(message).addClass('has-error');
      }

      // toggle error states
      formGroup.parents('fieldset').find('legend').toggleClass('has-error', !isValid);
      formGroup.toggleClass('has-error', !isValid);

      return isValid;
    },


    validateForm: function() {
      var isValid = true;

      // campaign country and type
      isValid = this.validateField($('.form-group.campaign_country'), this.validateSelected, 'Select a country') && isValid;
      isValid = this.validateField($('.form-group.campaign_type'), this.validateNestedSelect, 'Select a type') && isValid;

      // campaign sub-type
      isValid = this.validateField($('.form-group.campaign_subtype'), this.validateState, 'Select a sub-type') && isValid;

      // campaign segmentation
      isValid = this.validateField($('.form-group.segment_by'), this.validateSegmentBy, 'Campaign type requires custom targeting') && isValid;
      isValid = this.validateField($('.form-group.locate_by'), this.validateLocateBy, 'Please pick a location attribute') && isValid;
      
      // campaign targets
      isValid = this.validateField($('.form-group#set-targets'), this.validateTargetList, 'Add a custom target') && isValid;
      isValid = this.validateField($('.form-group.special_targets'), this.validateSpecialTargets, 'Please pick an order for Special Targets') && isValid;

      // phone numbers
      isValid = this.validateField($('.form-group.phone_number_set'), this.validateSelected, 'Select a phone number') && isValid;
      
      return isValid;
    },

    submitForm: function(event) {
      if (this.validateForm()) {
        this.targetListView.serialize();
        $(this.$el).unbind('submit').submit();
        return true;
      }
      return false;
    }

  });

})();
