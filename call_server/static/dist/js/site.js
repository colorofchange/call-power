/*global $, _*/

window.CallPower = _.extend(window.CallPower || {}, {
    Models: {},
    Collections: {},
    Views: {},
    Routers: {},
    init: function () {
        console.log('Call Power');

        new this.Routers.Campaign({});
    }
});

window.renderTemplate = function(selector, context) {
    var template = _.template($('script[type="text/template"]'+selector).html(), { 'variable': 'data' });
    return $(template(context));
};

window.flashMessage = function(message, status, global) {
    if (status === undefined) { var status = 'info'; }
    var flash = $('<div class="alert alert-'+status+'">'+
                          '<button type="button" class="close" data-dismiss="alert">×</button>'+
                          message+'</div>');
    if (global) {
        $('#global_message_container').empty().append(flash).show();
    } else {
        $('#flash_message_container').append(flash);
    }
};

$(document).ready(function () {
    var csrftoken = $('meta[name=csrf-token]').attr('content');

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    CallPower.init();
    Backbone.history.start({pushState: true, root: "/admin/"});
});

/*global CallPower, Backbone */

(function () {
  CallPower.Views.CampaignAudioForm = Backbone.View.extend({
    el: $('form#audio'),

    events: {
      'click .record': 'onRecord',
      'click .play': 'onPlay',
      'click .upload': 'onUpload',
      'click .version': 'onVersion',

      'submit': 'submitForm'
    },

    requiredFields: ['msg_intro', 'msg_call_block_intro'],

    initialize: function() {
      window.AudioContext = window.AudioContext || window.webkitAudioContext;
      navigator.getUserMedia = ( navigator.getUserMedia ||
                       navigator.webkitGetUserMedia ||
                       navigator.mozGetUserMedia ||
                       navigator.msGetUserMedia);
      window.URL = window.URL || window.webkitURL;

      if (CallPower.Config.TWILIO_CAPABILITY) {
        this.setupTwilioClient(CallPower.Config.TWILIO_CAPABILITY);
      }

      // add required fields client-side
      _.each(this.requiredFields, function(f) {
        $('label[for='+f+']').addClass('required');
      });

      this.campaign_id = $('input[name="campaign_id"]').val();
      this.campaign_language = $('input[name="campaign_language"]').val();

      $('audio', this.el).on('ended', this.onPlayEnded);
      _.bindAll(this, 'onPlayEnded');
    },

    onRecord: function(event) {
      event.preventDefault();

      // pull modal info from related fields
      var inputGroup = $(event.target).parents('.input-group');
      var modal = { name: inputGroup.prev('label').text(),
                    key: inputGroup.prev('label').attr('for'),
                    description: inputGroup.find('.description .help-inline').text(),
                    example_text: inputGroup.find('.description .example-text').text(),
                    campaign_id: this.campaign_id,
                    campaign_language: this.campaign_language,
                  };
      // and api
      var self = this;
      $.getJSON('/api/campaign/'+this.campaign_id,
          function(data) {
            var recording = data.audio_msgs[modal.key];

            if (recording === undefined) {
              return false;
            }
            if (recording.substring(0,4) == 'http') {
              modal.filename = recording;
            } else {
              modal.text_to_speech = recording;
          }
        }).then(function() {
          self.microphoneView = new CallPower.Views.MicrophoneModal();
          self.microphoneView.render(modal);
        });
    },

    onPlay: function(event) {
      event.preventDefault();
      
      var button = $(event.currentTarget); //.closest('button.play');
      var inputGroup = button.parents('.input-group');
      var key = inputGroup.prev('label').attr('for');
      var audio = button.children('audio')[0];
      
      if (audio.src) {
        // has src url set, play/pause

        if (audio.duration > 0 && !audio.paused) {
          // playing, pause
          audio.pause();

          button.children('.glyphicon').removeClass('glyphicon-pause').addClass('glyphicon-play');
          button.children('.text').html('Play');
          return false;
        } else {
          // paused, play
          audio.play();

          button.children('.glyphicon').removeClass('glyphicon-play').addClass('glyphicon-pause');
          button.children('.text').html('Pause');
          return false;
        }
      } else {
        // load src url from campaign
        var self = this;
        $.getJSON('/api/campaign/'+self.campaign_id,
          function(data) {
            var recording = data.audio_msgs[key];

            if (recording === undefined) {
              button.addClass('disabled');
              return false;
            }
            if (recording.substring(0,4) == 'http') {
              // play file url through <audio> object
              audio.setAttribute('src', data.audio_msgs[key]);
              audio.play();

              button.children('.glyphicon').removeClass('glyphicon-play').addClass('glyphicon-pause');
              button.children('.text').html('Pause');
            } else if (self.twilio) {
              console.log('twilio text-to-speech',recording);
              self.twilio.connect({
                'text': recording,
                'voice': 'alice',
                'lang': self.campaign_language,
            });

              button.children('.glyphicon').removeClass('glyphicon-play').addClass('glyphicon-bullhorn');
              button.children('.text').html('Speak');
          } else {
            button.addClass('disabled');
            return false;
          }
        });
      }
    },

    onPlayEnded: function(event) {
      var button = $(event.target).parents('.btn');
      button.children('.glyphicon').removeClass('glyphicon-pause').addClass('glyphicon-play');
      button.children('.text').html('Play');
    },

    setupTwilioClient: function(capability) {
      //connect twilio API to read text-to-speech
      try {
        this.twilio = Twilio.Device.setup(capability, {"debug":CallPower.Config.DEBUG | false});
      } catch (e) {
        console.error(e);
        msg = 'Sorry, your browser does not support WebRTC, Text-to-Speech playback may not work.<br/>' +
              'Check the list of compatible browsers at <a href="https://support.twilio.com/hc/en-us/articles/223180848-Which-browsers-support-WebRTC-">Twilio support</a>.';
        window.flashMessage(msg, 'warning');
        return false;
      }

      this.twilio.incoming(function(connection) {
        connection.accept();
        // do awesome ui stuff here
        // $('#call-status').text("you're on a call!");
      });
      this.twilio.error(function(error) {
        console.error(error);
        var message = error.info ? error.info.message : error.message;
        if (message == "Invalid application SID") {
          message = message + "<br> Ensure TwiML Application $TWILIO_PLAYBACK_APP will POST to /api/twilio/text-to-speech";
        }
        if (error.info) {
          message = 'Twilio error: '+error.info.code+' '+message;
        }
        window.flashMessage(message, 'info');
      });
      this.twilio.connect(function(conn) {
        console.log('Twilio connection', conn.status());
      });
      this.twilio.disconnect(this.onPlayEnded);
    },

    onVersion: function(event) {
      event.preventDefault();

      var inputGroup = $(event.target).parents('.input-group');
      var modal = {
        name: inputGroup.prev('label').text(),
        key: inputGroup.prev('label').attr('for'),
        campaign_id: this.campaign_id
      };
      this.versionsView = new CallPower.Views.VersionsModal(modal);
      this.versionsView.render();
    },

    validateForm: function() {
      var isValid = true;

      // check required fields for valid class
      _.each(this.requiredFields, function(f) {
        var formGroup = $('.form-group.'+f);
        var fieldValid = formGroup.hasClass('valid');
        if (!fieldValid) {
          formGroup.find('.input-group .help-block')
            .text('This field is required.')
            .addClass('error');
        }
        isValid = isValid && fieldValid;
      });

      // call validators
      
      return isValid;
    },

    submitForm: function(event) {
      if (this.validateForm()) {
        $(this.$el).unbind('submit').submit();
        return true;
      }
      return false;
    }

  });

})();
/*global CallPower, Backbone */

(function () {
    CallPower.Models.Call = Backbone.Model.extend({
    defaults: {
      id: null,
      timestamp: null,
      campaign_id: null,
      target_id: null,
      call_id: null,
      status: null,
      duration: null
    },
  });


  CallPower.Collections.CallList = Backbone.PageableCollection.extend({
    model: CallPower.Models.Call,
    url: '/api/call',
    // turn off PageableCollection queryParams by setting to null
    // per https://github.com/backbone-paginator/backbone.paginator/issues/240
    queryParams: {
      pageSize: null,
      currentPage: "page",
      totalRecords: null,
      totalPages: null,
    },
    state: {
      firstPage: 1,
      pageSize: 10,
      sortKey: "timestamp",
      direction: -1,
    },

    initialize: function(campaign_id) {
      this.campaign_id = campaign_id;
    },

    parseRecords: function(response) {
      return response.objects;
    },

    parseState: function (resp, queryParams, state, options) {
      return {
        currentPage: resp.page,
        totalRecords: resp.num_results
      };
    },

    fetch: function() {
      // transform filters and pagination to flask-restless style
      // always include campaign_id filter
      var filters = [{name: 'campaign_id', op: 'eq', val: this.campaign_id}];
      if (this.filters) {
        Array.prototype.push.apply(filters, this.filters);
      }
      // calculate offset from currentPage * pageSize, accounting for 1-base
      var currentOffset = Math.max(this.state.currentPage*-1, 0) * this.state.pageSize;
      var flaskQuery = {
        filters: filters,
        offset: currentOffset,
        order_by: [{
          field: this.state.sortKey,
          direction: this.state.direction == -1 ? "asc" : "desc"
        }]
      };
      var fetchOptions = _.extend({ data: {
        q: JSON.stringify(flaskQuery)
      }});
      return Backbone.PageableCollection.prototype.fetch.call(this, fetchOptions);
    }
  });

  CallPower.Views.CallItemView = Backbone.View.extend({
    tagName: 'tr',

    initialize: function() {
      this.template = _.template($('#call-log-tmpl').html(), { 'variable': 'data' });
    },

    render: function() {
      var data = this.model.toJSON();
      var html = this.template(data);
      this.$el.html(html);
      return this;
    },
  });

  CallPower.Views.CallLog = Backbone.View.extend({
    el: $('#call_log'),
    el_paginator: $('#calls-list-paginator'),

    events: {
      'change .filters input': 'updateFilters',
      'change .filters select': 'updateFilters',
      'click .filters button.search': 'searchCallIds',
      'blur input[name="call-search"]': 'searchCallIds',
      'click a.info-modal': 'showInfoModal',
    },


    initialize: function(campaign_id) {
      this.collection = new CallPower.Collections.CallList(campaign_id);
      this.listenTo(this.collection, 'reset add remove', this.renderCollection);
      this.views = [];

      this.$el.find('.input-daterange input').each(function (){
        $(this).datepicker({
          'format': "yyyy/mm/dd",
          'orientation': 'top',
        });
      });

      this.updateFilters();
    },

    pagingatorPage: function(event, num){
      this.collection.getPage(num);
    },

    updateFilters: function(event) {
      var status = $('select[name="status"]').val();
      var start = new Date($('input[name="start"]').datepicker('getDate'));
      var end = new Date($('input[name="end"]').datepicker('getDate'));
      var call_sids = JSON.parse($('input[name="call_sids"]').val());

      if (start > end) {
        $('.input-daterange input[name="start"]').addClass('error');
        return false;
      } else {
        $('.input-daterange input').removeClass('error');
      }

      var filters = [];
      if (status) {
        filters.push({'name': 'status', 'op': 'eq', 'val': status});
      }
      if (start) {
        filters.push({'name': 'timestamp', 'op': 'gt', 'val': start.toISOString()});
      }
      if (end) {
        filters.push({'name': 'timestamp', 'op': 'lt', 'val': end.toISOString()});
      }
      if(call_sids) {
        filters.push({'name': 'call_id', 'op': 'in', 'val': call_sids});
      }
      this.collection.filters = filters;

      var self = this;
      this.collection.fetch().then(function() {
        // reset paginator with new results
        self.el_paginator.bootpag({
          total: self.collection.state.totalPages,
          page: self.collection.state.currentPage,
          maxVisible: 5,
        }).on('page', _.bind(self.pagingatorPage, self));
      });
    },

    searchCallIds: function() {
      var self = this;

      var search_phone = $('input[name="call-search"]').val();
      if (!search_phone)
        return false;

      $.getJSON('/api/twilio/calls/to/'+search_phone+'/',
          function(data) {
            $('input[name="call_sids"]').val(JSON.stringify(data.objects));
        }).then(function() {
          self.updateFilters();
        });
    },

    renderCollection: function() {
      var self = this;

      // clear any existing subviews
      this.destroyViews();
      var $list = this.$('table tbody').empty();

      // create subviews for each item in collection
      this.views = this.collection.map(this.createItemView, this);
      $list.append( _.map(this.views,
        function(view) { return view.render(self.campaign_id).el; },
        this)
      );

      var renderedItems = this.$('table tbody tr');
      if (renderedItems.length === 0) {
        this.$('table tbody').html('<p>No results. Try adjusting filters.</p>');
      }
    },

    destroyViews: function() {
      // destroy each subview
      _.invoke(this.views, 'destroy');
      this.views.length = 0;
    },

    createItemView: function (model) {
      return new CallPower.Views.CallItemView({ model: model });
    },

    showInfoModal: function (event) {
      var sid = $(event.target).data('sid');
      $.getJSON('/api/twilio/calls/info/'+sid+'/',
          function(data) {
            data.sid = sid;
            return (new CallPower.Views.CallInfoView(data)).render();
        });
    },

  });
  
  CallPower.Views.CallInfoView = Backbone.View.extend({
    tagName: 'div',
    className: 'microphone modal fade',

    initialize: function(data) {
      this.data = data;
      this.template = _.template($('#call-info-tmpl').html(), { 'variable': 'data' });
    },

    render: function() {
      var html = this.template(this.data);
      this.$el.html(html);

      this.$el.on('hidden.bs.modal', this.destroy);
      this.$el.modal('show');

      return this;
    },

    destroy: function() {
      this.undelegateEvents();
      this.$el.removeData().unbind();

      this.remove();
      Backbone.View.prototype.remove.call(this);
    },
  });


})();
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

/*global CallPower, Backbone */

(function () {
  CallPower.Views.CampaignLaunchForm = Backbone.View.extend({
    el: $('#launch'),

    events: {
      'change select#test_call_country': 'changeTestCallCountry',
      'click .test-call': 'makeTestCall',
      'change #embed_type': 'toggleEmbedPanel',
      'blur #custom_embed_options input': 'updateEmbedCode',
      'change #custom_embed_options select': 'updateEmbedCode',
      'change #embed_script_display': 'updateEmbedScriptDisplay',
    },

    initialize: function() {
      this.campaignId = $('#campaignId').val();
      $('.readonly').attr('readonly', 'readonly');
      this.toggleEmbedPanel();
    },

    changeTestCallCountry: function() {
      var country = $('#test_call_country').val();
      if (!country) {
        $('#test_call_country_other').removeClass('hidden')
        country = $('#test_call_country_other').val();
      } else {
        $('#test_call_country_other').addClass('hidden').val('');
      }
    },

    makeTestCall: function(event) {
      var statusIcon = $(event.target).next('.glyphicon');
      statusIcon.removeClass('error').addClass('glyphicon-earphone');
      if (window.location.hostname === 'localhost') {
        alert("Call Power cannot place test calls unless hosted on an externally routable address. Try using ngrok and restarting with the --server option.");
        $(event.target).addClass('disabled');
        statusIcon.addClass('error');
        return false;
      }

      statusIcon.addClass('active');

      var phone = $('#test_call_number').val();
      phone = phone.replace(/\s/g, '').replace(/\(/g, '').replace(/\)/g, ''); // remove spaces, parens
      phone = phone.replace("+", "").replace(/\-/g, ''); // remove plus, dash

      var location = $('#test_call_location').val();
      var country = $('#test_call_country').val() || $('#test_call_country_other').val();
      var record = $('#test_call_record:checked').val();

      $.ajax({
        url: '/call/create',
        data: {campaignId: this.campaignId,
          userPhone: phone,
          userLocation: location,
          userCountry: country,
          record: record
        },
        success: function(data) {
          alert('Calling you at '+$('#test_call_number').val()+' now!');
          if (data.call == 'queued') {
            statusIcon.removeClass('active').addClass('success');
            $('.form-group.test_call .controls .help-block').removeClass('has-error').text('');
          } else {
            console.error(data);
            statusIcon.addClass('error');
            $('.form-group.test_call .controls .help-block').addClass('has-error').text(data.responseText);
          }
        },
        error: function(err) {
          console.error(err);
          statusIcon.addClass('error');
          var errMessage = err.responseJSON.error || 'unknown error';
          $('.form-group.test_call .controls .help-block').addClass('has-error').text(errMessage);
        }
      });
    },

    toggleEmbedPanel: function(event) {
      var formType = $('#embed_type').val();
      if (formType) {
        $('.form-group.embed_code').removeClass('hidden');
      } else {
        $('.form-group.embed_code').addClass('hidden');
      }

      if (formType === 'custom' || formType === 'iframe') {
        $('#embed_options').collapse('show');
      } else {
        $('#embed_options').collapse('hide');
      }
      if (formType === 'iframe') {
        $('#embed_options h3').text('iFrame Embed Options');
        $('#embed_options .form-group').hide().filter('.iframe').show();
      } else {
        $('#embed_options h3').text('Javascript Embed Options');
        $('#embed_options .form-group').show();
      }

      this.updateEmbedCode();
      this.updateEmbedScriptDisplay();
    },

    updateEmbedCode: function(event) {
      $.ajax({
        url: '/api/campaign/'+this.campaignId+'/embed_code.html',
        data: {
          'embed_type': $('#embed_type').val(),
          'embed_form_sel': $('#embed_form_sel').val(),
          'embed_phone_sel': $('#embed_phone_sel').val(),
          'embed_location_sel': $('#embed_location_sel').val(),
          'embed_custom_css': $('#embed_custom_css').val(),
          'embed_custom_js': $('#embed_custom_js').val(),
          'embed_script_display': $('#embed_script_display').val(),
        },
        success: function(html) {
          $('textarea#embed_code').val(html);
        }
      });
    },

    updateEmbedScriptDisplay: function(event) {
      var formType = $('#embed_type').val();
      var scriptDisplay = $('#embed_script_display').val();
      
      $('#embed_options .form-group.redirect').toggle(scriptDisplay === 'redirect');
      $('#embed_options .form-group.custom').toggle(scriptDisplay === 'custom');
      $('#embed_options .form-group.iframe').toggle(formType === 'iframe');
    },

  });

})();
/*global CallPower, Backbone, createAudioMeter */

/* Code adapted from volume-meter/main.js
* Copyright (c) 2014 Chris Wilson
* Available under the MIT License
*/

(function () {
  CallPower.Views.AudioMeter = Backbone.View.extend({
    el: $('.meter'),

    initialize: function(recorder) {
      this.template = _.template($('#meter-canvas-tmpl').html());

      // bind getUserMedia triggered events to this backbone view
      _.bindAll(this, 'drawLoop');

      this.meter = null;
      this.WIDTH = 500; // default, gets reset on page render
      this.HEIGHT = 30; // match button height
      this.canvasContext = null;
      this.rafID = null;

      // get stream source from audio context
      this.mediaStreamSource = recorder.source;
      this.meter = createAudioMeter(recorder.context);
      this.mediaStreamSource.connect(this.meter);
    },

    render: function() {
      this.$el = $('.meter'); // re-bind once element is created

      var html = this.template({WIDTH: this.WIDTH, HEIGHT: this.HEIGHT});
      this.$el.html(html);

      // get canvas context
      this.canvasContext = document.getElementById( "meter" ).getContext("2d");

      // and newly calculated canvas width
      this.WIDTH = $('#meter').width();
      $('#meter').attr('width', this.WIDTH);

      // kick off the visual updating
      this.drawLoop();

      return this;
    },

    drawLoop: function(time) {
      // clear the background
      this.canvasContext.clearRect(0,0,this.WIDTH,this.HEIGHT);

      // check if we're currently clipping
      if (this.meter.checkClipping())
          this.canvasContext.fillStyle = "red";
      else
          this.canvasContext.fillStyle = "green";

      // draw a bar based on the current volume
      this.canvasContext.fillRect(0, 0, this.meter.volume*this.WIDTH*1.4, this.HEIGHT);

      // set up the next visual callback
      this.rafID = window.requestAnimationFrame( this.drawLoop );
    },

    destroy: function() {
      this.meter.shutdown();
      this.undelegateEvents();
      this.$el.removeData().unbind();

      this.remove();
      Backbone.View.prototype.remove.call(this);
    },

  });

})();
/*global CallPower, Backbone, audioRecorder */

(function () {
  CallPower.Views.MicrophoneModal = Backbone.View.extend({
    tagName: 'div',
    className: 'microphone modal fade',

    events: {
      'change select.source': 'setSource',
      'click .nav-tabs': 'switchTab',
      'click .btn-record': 'onRecord',
      'change input[type="file"]': 'chooseFile',
      'blur textarea[name="text_to_speech"]': 'validateTextToSpeech',
      'submit': 'onSave'
    },

    initialize: function() {
      this.template = _.template($('#microphone-modal-tmpl').html(), { 'variable': 'modal' });
      _.bindAll(this, 'setup', 'confirmClose', 'destroy', 'getSources', 'streamError', 'connectRecorder', 'dataAvailable');
    },

    render: function(modal) {
      this.modal = modal;
      var html = this.template(modal);
      this.$el.html(html);

      this.$el.on('shown.bs.modal', this.setup);
      this.$el.on('hide.bs.modal', this.confirmClose);
      this.$el.on('hidden.bs.modal', this.destroy);
      this.$el.modal('show');

      return this;
    },

    setup: function() {
      if (this.isRecordingSupported()) {
        $('.nav-tabs a[href="#record"]', this.$el).tab('show');

        // get available sources (Chrome only)
        if (MediaStreamTrack.getSources !== undefined) {
          MediaStreamTrack.getSources( this.getSources );
        } else {
          this.setSource();
        }
      } else {
        // switch to upload tab
        $('.nav-tabs a[href="#upload"]', this.$el).tab('show');

        // disable record tab
        $('.nav-tabs a[href="#record"]', this.$el).parent('li').addClass('disabled')
          .attr('title','Sorry, recording is not supported in this browser.');
      }

      this.playback = $('audio[name="playback"]', this.$el);
    },

    isRecordingSupported: function() {
      return !!(navigator.getUserMedia || navigator.webkitGetUserMedia ||
                navigator.mozGetUserMedia || navigator.msGetUserMedia);
    },

    switchTab: function(event) {
      event.preventDefault();
      // set up tab behavior manually instead of relying on data-toggle
      // because we have multiple modals on the page and IDs could conflict

      var tabID = $(event.target).attr('href');
      var tab = $('.nav-tabs a[href="'+tabID+'"]', this.$el);
      if (!tab.parent('li').hasClass('disabled')) {
        tab.tab('show');
      }
      return true;
    },

    confirmClose: function(event) {
      if (this.recorder && this.recorder.state === 'recording') {
        return false;
      }

      if (!!this.playback.attr('src') && !this.saved) {
        // there is audio in the player, but not yet saved
        return confirm('You have recorded unsaved audio. Are you sure you want to close?');
      } else {
        return true;
      }
    },

    destroy: function() {
      if (this.recorder) {
        this.recorder.stop();
        this.meter.destroy();
      }
      this.undelegateEvents();
      this.$el.removeData().unbind();

      this.remove();
      Backbone.View.prototype.remove.call(this);
    },

    streamError: function(e) {
      this.recorder.state = "error";

      var msg = 'Please allow microphone access in the permissions popup.';
      if (window.chrome !== undefined) {
        msg = msg + '<br>You may need to remove this site from your media exceptions at <a href="">chrome://settings/content</a>';
      }
      window.flashMessage(msg, 'warning', true);
    },

    getSources: function(sourceInfos) {
      // fill in source info in selector
      sourceSelect = $('select.source', this.$el);
      sourceSelect.empty();

      for (var i = 0; i !== sourceInfos.length; ++i) {
        var sourceInfo = sourceInfos[i];
        var option = $('<option></option>');
        option.val(sourceInfo.id);
        if (sourceInfo.kind === 'audio') {
          option.text(sourceInfo.label || 'Microphone ' + (sourceSelect.children('option').length + 1));
          sourceSelect.append(option);
        }
      }
      this.setSource();
    },

    setSource: function() {
      var selectedSourceId = $('select.source', this.$el).children('option:selected').val();

      var mediaConstraints = { audio: {
            mandatory: {
              // disable chrome filters
              googEchoCancellation: false,
              googAutoGainControl: false,
              googNoiseSuppression: false,
              googHighpassFilter: false
            }
        }
      };

      if (selectedSourceId) {
         // set selected source in config
        mediaConstraints.audio.optional = [{ sourceId: selectedSourceId }];
      } // if not, uses default

      navigator.getUserMedia(mediaConstraints, this.connectRecorder, this.streamError);
    },

    connectRecorder: function(stream) {
      var audioContext = new AudioContext;
      var source = audioContext.createMediaStreamSource(stream);

      var recorderConfig = {
        workerPath: '/static/dist/js/lib/recorderWorker.js',
        mp3LibPath: '/static/dist/js/lib/lame.all.js',
        vorbisLibPath: '/static/dist/js/lib/lame.all.js', // not really, but we only want mp3 recording
        // reuse exisiting path to avoid double downloading large emscripten compiled js
        recordAsMP3: true,
        bitRate: 8,

      };
      this.recorder  = audioRecorder.fromSource(source, recorderConfig);
      this.recorder.context = audioContext;
      this.recorder.source = source;
      this.recorder.state = 'inactive';

       // connect audio meter
      this.meter = new CallPower.Views.AudioMeter(this.recorder);
      this.meter.render();
    },

    onRecord: function(event) {
      event.preventDefault();

       // track custom state beyond what audioRecord.js provides

      if (this.recorder.state === 'error') {
        // reset source
        this.setSource();
      }
      else if (this.recorder.state === 'inactive') {
        // start recording
        this.recorder.record();
        this.recorder.state = 'recording';

        // show audio row and recording indicator
        $('.playback').show();
        $('.playback .status').addClass('active').show();

        // button to stop
        $('button.btn-record .glyphicon', this.$el).removeClass('glyphicon-record').addClass('glyphicon-stop');
        $('button.btn-record .text', this.$el).text('Stop');
      }
      else if (this.recorder.state === 'recording' || this.recorder.recording) {
        // stop recording
        this.recorder.stop();
        this.recorder.state = 'stopped';
        this.recorder.exportMP3(this.dataAvailable);

        $('.playback .status').removeClass('active').hide();

        // button to reset
        $('button.btn-record .glyphicon', this.$el).removeClass('glyphicon-stop').addClass('glyphicon-step-backward');
        $('button.btn-record .text', this.$el).text('Reset');
      }
      else if (this.recorder.state === 'stopped') {
        // clear buffers and restart
        this.recorder.clear();
        this.recorder.state = 'inactive';

        // clear playback
        this.playback.attr('controls', false);
        this.playback.attr('src', '');
        $('.playback').hide();

        // button to record
        $('button.btn-record .glyphicon', this.$el).removeClass('glyphicon-step-backward').addClass('glyphicon-record');
        $('button.btn-record .text', this.$el).text('Record');
      }
      else {
        console.error('recorder in invalid state');
      }
    },

    dataAvailable: function(data) {
      console.log('dataAvailable', this, data);
      this.audioBlob = data;
      this.playback.attr('controls', true);
      this.playback.attr('src',URL.createObjectURL(this.audioBlob));

      // reload media blob when done playing, because Chrome won't do it automatically
      this.playback.on('ended', function() {
        this.load();
      });
    },

    chooseFile: function() {
      this.filename = $('input[type="file"]').val().split(/(\\|\/)/g).pop();
      $('span.filename').text(this.filename);
    },

    validateTextToSpeech: function() {
      // TODO, run through simple jinja-like validator
      // provide auto-completion of available context?

      this.textToSpeech = $('textarea[name="text_to_speech"]').val();
    },

    validateField: function(parentGroup, validator, message) {
      // run validator for parentGroup, if present
      if (!parentGroup.length) {
        return true;
      }

      var isValid = validator(parentGroup);
      
      // put message in last help-block
      $('.help-block', parentGroup).last().text((!isValid) ? message : '');

      // toggle error states
      parentGroup.toggleClass('has-error', !isValid);
      return isValid;
    },


    validateForm: function() {
      var isValid = true;
      var self = this;

      if (!$('.tab-pane#record').hasClass('active')) {
        // if we are not on the recording tab, delete the blob
        delete this.audioBlob;
      }

      isValid = this.validateField($('.tab-pane.active#record'), function() {
        return !!self.playback.attr('src');
      }, 'Please record your message') && isValid;

      isValid = this.validateField($('.tab-pane.active#upload'), function() {
        return !!self.filename;
      }, 'Please select a file to upload') && isValid;

      isValid = this.validateField($('.tab-pane.active#upload'), function() {
        return _.includes(['mp3','wav','aif','aiff','gsm','ulaw'], self.filetype.toLowerCase());
      }, 'Uploaded file must be an MP3 or WAV. M4A or iPhone Voice Memos will not play back.') && isValid;

      isValid = this.validateField($('.tab-pane.active#text-to-speech'), function() {
        return !!self.textToSpeech;
      }, 'Please enter text to read') && isValid;

      return isValid;
    },

    onSave: function(event) {
      event.preventDefault();

      // change save button to spinner
      $('.btn.save .glyphicon')
        .removeClass('glyphicon-circle-arrow-down')
        .addClass('glyphicon-refresh')
        .addClass('glyphicon-spin');

      // submit file via ajax with html5 FormData
      // probably will not work in old IE
      var formData = new FormData();
      
      // add inputs individually, so we can control how we add files
      var formItems = $('form.modal-body', this.$el).find('input[type!="file"], select, textarea');
      _.each(formItems, function(item) {
        var $item = $(item);
        if ($item.val()) {
          formData.append($item.attr('name'), $item.val());
        }
      });
      // create file from blob
      if (this.audioBlob) {
        formData.append('file_storage', this.audioBlob);
        formData.append('file_type', 'mp3');
      } else if (this.filename) {
        var fileData = $('input[type="file"]')[0].files[0];
        formData.append('file_storage', fileData);
        
        var fileType = fileData.name.split('.').pop(-1);
        formData.append('file_type', fileType);
        this.filetype = fileType;
      }

      var self = this;
      if (this.validateForm()) {
        $(this.$el).unbind('submit').submit();
        $.ajax($('form.modal-body').attr('action'), {
          method: "POST",
          data: formData,
          processData: false, // stop jQuery from munging our carefully constructed FormData
          contentType: false, // or faffing with the content-type
          success: function(response) {
            if (response.success) {
              // build friendly message like "Audio recording uploaded: Introduction version 3"
              var fieldDescription = $('form label[for="'+response.key+'"]').text();
              var msg = response.message + ': '+fieldDescription + ' version ' + response.version;
              // and display to user
              window.flashMessage(msg, 'success');

              // update parent form-group status and description
              var parentFormGroup = $('.form-group.'+response.key);
              parentFormGroup.addClass('valid');
              parentFormGroup.find('.input-group .help-block').text('');
              parentFormGroup.find('.description .status').addClass('glyphicon-check');

              // close the parent modal
              self.saved = true;
              self.$el.modal('hide');
            } else {
              console.error(response);
              window.flashMessage(response.errors, 'error', true);
            }
          },
          error: function(xhr, status, error) {
            console.error(status, error);
            window.flashMessage(error, 'error');
          }
        });
        this.delegateEvents(); // re-bind the submit handler
        return true;
      }
      return false;
    },

  });

})();
(function () {
  CallPower.Routers.Campaign = Backbone.Router.extend({
    routes: {
      "campaign/create": "campaignForm",
      "campaign/create/:country/:type": "campaignForm",
      "campaign/:id/edit": "campaignForm",
      "campaign/:id/edit-type": "campaignForm",
      "campaign/:id/copy": "campaignForm",
      "campaign/:id/audio": "audioForm",
      "campaign/:id/launch": "launchForm",
      "campaign/:id/calls": "callLog",
      "system": "systemForm",
      "statistics": "statisticsView",
    },

    campaignForm: function(id) {
      CallPower.campaignForm = new CallPower.Views.CampaignForm();
    },

    audioForm: function(id) {
      CallPower.campaignAudioForm = new CallPower.Views.CampaignAudioForm();
    },

    launchForm: function(id) {
      CallPower.campaignLaunchForm = new CallPower.Views.CampaignLaunchForm();
    },

    callLog: function(id) {
      CallPower.callLog = new CallPower.Views.CallLog(id);
    },

    systemForm: function() {
      CallPower.systemForm = new CallPower.Views.SystemForm();
    },

    statisticsView: function() {
      CallPower.statisticsView = new CallPower.Views.StatisticsView();
    }
  });
})();
/*global CallPower, Backbone */

(function () {
  CallPower.Views.TargetSearch = Backbone.View.extend({
    el: $('div#target-search'),

    events: {
      // target search
      'keydown input[name="target-search"]': 'searchKey',
      'focusout input[name="target-search"]': 'searchTab',
      'click .search-field .dropdown-menu li a': 'searchField',
      'click .search': 'doTargetSearch',
      'click .search-results .result': 'selectSearchResult',
      'click .search-results .close': 'closeSearch',
    },

    initialize: function() { },

    searchKey: function(event) {
      if(event.which === 13) { // enter key
        event.preventDefault();
        this.doTargetSearch();
      }
    },

    searchTab: function(event) {
      // TODO, if there's only one result add it
      // otherwise, let user select one
    },

    searchField: function(event) {
      event.preventDefault();
      var selectedField = $(event.currentTarget);
      $('.search-field button').html(selectedField.text()+' <span class="caret"></span>');
      $('input[name=search_field]').val(selectedField.attr('id'));
    },

    doTargetSearch: function(event) {
      var self = this;

      var campaign_country = $('select[name="campaign_country"]').val();
      var campaign_type = $('select[name="campaign_type"]').val();
      var campaign_state = $('select[name="campaign_state"]').val();
      var search_field = $('input[name=search_field]').val();

      // search the political data cache by default
      var query = $('input[name="target-search"]').val();
      var searchURL = '/political_data/search';
      var searchData = {
        'country': campaign_country,
        'key': query // default to full text search
      };

      if (!search_field) {
        self.errorSearchResults({status: 'warning', message: 'Select a field to search'});
        return false;
      }

      if (query.length < 2) {
        self.errorSearchResults({status: 'warning', message: 'Search query must be at least two characters long'});
        return false;
      }

      if (campaign_country === 'us') {
        var chamber = $('select[name="campaign_subtype"]').val();

        if (search_field === 'state') {
          query = query.toUpperCase();
          if (query.length > 2) {
            self.errorSearchResults({status: 'danger', message: 'Search by state abbreviation'});
            return false;
          }
        }

        if (search_field === 'last_name') {
          searchData['filter'] = 'last_name='+query;
          query = ''; // clear query, used as filter value
        }

        if (campaign_type === 'congress') {
          // format key by chamber
          if (chamber === 'lower') {
              searchData['key'] = 'us:house:'+query;
          }
          if (chamber === 'upper') {
            searchData['key'] = 'us:senate:'+query;
          }
          if (chamber === 'both') {
            // use jQuery param to send multiple values
            var filter = searchData['filter'];
            searchData = $.param({
              'key': ['us:house:'+query, 'us:senate:'+query],
              'filter': filter
            }, true);
          }
        }

        if (campaign_type === 'state') {
          if (chamber === 'exec') {
            // search using our own data
            searchData['key'] = 'us_state:governor:'+query;
          } else {
            // hit OpenStates
            searchURL = CallPower.Config.OPENSTATES_URL;
            searchData = {
              apikey: CallPower.Config.OPENSTATES_API_KEY,
              state: campaign_state,
            }
            if (chamber === 'upper' || chamber === 'lower') {
              searchData['chamber'] = chamber;
            } // if both, don't limit to a chamber
            // query may have been cleared, get value from input
            searchData[search_field] = $('input[name="target-search"]').val();
          }
        }
      }

      if (campaign_country === 'ca') {
        var baseURL = CallPower.Config.OPENNORTH_URL;
        // reset search data to match OpenNorth
        searchData = {};
        
        if (campaign_type === 'parliament') {
          searchURL = baseURL + 'representatives/house-of-commons/';
          searchData[search_field] = query;
        }

        if (campaign_type === 'province') {
          var CA_PROVINCE_BODIES = {
            'AB': 'alberta-legislature',
            'BC': 'bc-legislature',
            'MB': 'manitoba-legislature',
            'NB': 'new-brunswick-legislature',
            'NL': 'newfoundland-labrador-legislature',
            'NS': 'nova-scotia-legislature',
            'ON': 'ontario-legislature',
            'PE': 'pei-legislature',
            'QC': 'quebec-assemblee-nationale',
            'SK': 'saskatchewan-legislature',
           }
          searchURL = baseURL + 'representatives/'+CA_PROVINCE_BODIES[campaign_state];
          searchData[search_field] = query;
        }
      }

      $.ajax({
        url: searchURL,
        data: searchData,
        success: self.renderSearchResults,
        error: self.errorSearchResults,
        beforeSend: function(jqXHR, settings) { console.log(settings.url); },
      });

      // start spinner
      $('.btn.search .glyphicon').removeClass('glyphicon-search').addClass('glyphicon-repeat spin');
      $('.btn.search').attr('disabled','disabled');
      return true;
    },

    renderSearchResults: function(response) {
      // stop spinner
      $('.btn.search .glyphicon').removeClass('glyphicon-repeat spin').addClass('glyphicon-search');
      $('.btn.search').removeAttr('disabled');

      // clear existing results, errors
      $('.search-results .dropdown-menu').empty();
      $('.form-group#set-targets .search-help-block').empty();

      var results;
      if (response.results) {
        results = response.results;
      } if (response.objects) {
        // open north returns meta
        results = response.objects;
      }

      if (!results) {
        results = response;
      }

      var dropdownMenu = renderTemplate("#search-results-dropdown-tmpl");
      if (results.length === 0) {
        dropdownMenu.append('<li class="result close"><a>No results</a></li>');
      }

      _.each(results, function(person) {
        // standardize office titles
        if (person.title === 'Sen')  { person.title = 'Senator'; }
        if (person.title === 'Rep')  { person.title = 'Representative'; }
        if (person.elected_office === 'MP')  { person.title = 'MP'; }

        var uid_prefix = '';
        if (person.bioguide_id) {
          uid_prefix = 'us:bioguide:';
          person.uid = uid_prefix+person.bioguide_id;
        } else if (person.leg_id) {
          uid_prefix = 'us_state:openstates:';
          person.uid = uid_prefix+person.leg_id;
        } else if (person.title === 'Governor') {
          uid_prefix = 'us_state:governor:';
          person.uid = uid_prefix+person.state
        } else if (person.related && person.related.boundary_url) {
          var boundary_url = person.related.boundary_url.replace('/boundaries/', '/');
          person.uid = boundary_url;
        }

        // render the main office
        if (person.phone || person.tel) {
          var li = renderTemplate("#search-results-item-tmpl", person);
          dropdownMenu.append(li);
        }

        // then any others
        _.each(person.offices, function(office) {
          // normalize fields to person
          if (office.phone || office.tel) {
            office.title = person.title;
            office.first_name = person.first_name;
            office.last_name = person.last_name;
            office.uid = person.uid+(office.id || '');
            office.phone = office.phone || office.tel;
            office.office_name = office.name || office.city || office.type;
            var li = renderTemplate("#search-results-item-tmpl", office);
            dropdownMenu.append(li);
          }
        });
      });
      $('.input-group .search-results').append(dropdownMenu);
    },

    errorSearchResults: function(response) {
      var error_panel = $('<div class="alert alert-'+response.status+'">'+
                          '<button type="button" class="close" data-dismiss="alert">×</button>'+
                          response.message+'</div>');
      $('.form-group#set-targets .search-help-block').html(error_panel);
    },

    closeSearch: function() {
      var dropdownMenu = $('.search-results .dropdown-menu').remove();
    },

    selectSearchResult: function(event) {
      // get reference to collection from global
      var collection = CallPower.campaignForm.targetListView.collection;

      // pull json data out of data-object attr
      var obj = $(event.target).data('object');
      // force to appear at the end of the list
      obj.order = collection.length;
      // add it to the collection, triggers render and recalculateOrder
      collection.add(obj);

      // if only one result, closeSearch
      if ($('.search-results .dropdown-menu').children('.result').length <= 1) {
        this.closeSearch();
      }
    },

  });

})();
/*global CallPower, Backbone */

(function () {
  CallPower.Views.StatisticsView = Backbone.View.extend({
    el: $('#statistics'),
    campaignId: null,

    events: {
      'change select[name="campaigns"]': 'changeCampaign',
      'change select[name="timespan"]': 'renderChart',
      'click .btn.download': 'downloadTable',
    },

    initialize: function() {
      this.$el.find('.input-daterange input').each(function (){
        $(this).datepicker({
          'format': "yyyy/mm/dd"
        });
      });

      _.bindAll(this, 'renderChart');
      this.$el.on('changeDate', _.debounce(this.renderChart, this));

      this.chartOpts = {
        library: {
          canvasDimensions:{ height:250},
          xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: {
                day: '%b %e',
                week: '%b %e',
                month: '%b %y',
                year: '%Y',
            },
          },
          yAxis: { allowDecimals: false, min: null },
        }
      };
      this.summaryDataTemplate = _.template($('#summary-data-tmpl').html(), { 'variable': 'data' });
      this.targetDataTemplate = _.template($('#target-data-tmpl').html(), { 'variable': 'targets'});

      $.tablesorter.addParser({
        id: 'lastname',
        is: function(s) {
          return false;
        },
        format: function(s) {
          var parts = s.split(" ");
          return parts[1];
        },
        type: 'text'
      });

      this.renderChart();
    },

    changeCampaign: function(event) {
      var self = this;

      this.campaignId = $('select[name="campaigns"]').val();
      if (!this.campaignId) {
        self.renderChart();
        $('#summary_data').hide();
        return;
      }
      $.getJSON('/api/campaign/'+this.campaignId+'/stats.json',
        function(data) {
          if (data.sessions_completed && data.sessions_started) {
            var conversion_rate = (data.sessions_completed / data.sessions_started);
            conversion_pct = Number((conversion_rate*100).toFixed(2));
            data.conversion_rate = (conversion_pct+"%");
          } else {
            data.conversion_rate = 'n/a';
          }
          if (!data.sessions_completed) {
            data.calls_per_session = 'n/a';
          }
          $('#summary_data').html(
            self.summaryDataTemplate(data)
          ).show();

          if (data.date_start && data.date_end) {
            $('input[name="start"]').datepicker('setDate', data.date_start);
            $('input[name="end"]').datepicker('setDate', data.date_end);
          }
          self.renderChart();
        });
    },

    renderChart: function(event) {
      var self = this;

      var timespan = $('select[name="timespan"]').val();
      var start = new Date($('input[name="start"]').datepicker('getDate')).toISOString();
      var end = new Date($('input[name="end"]').datepicker('getDate')).toISOString();

      if (start > end) {
        $('.input-daterange input[name="start"]').addClass('error');
        return false;
      } else {
        $('.input-daterange input').removeClass('error');
      }

      if (this.campaignId) {
        var chartDataUrl = '/api/campaign/'+this.campaignId+'/date_calls.json?timespan='+timespan;
      } else {
        var chartDataUrl = '/api/campaign/date_calls.json?timespan='+timespan;
      }
      if (start) {
        chartDataUrl += ('&start='+start);
      }
      if (end) {
        chartDataUrl += ('&end='+end);
      }

      $('#chart_display').html('<span class="glyphicon glyphicon-refresh spin"></span> Loading...');
      $.getJSON(chartDataUrl, function(data) {
        if (self.campaignId) {
          // calls for this campaign by date, map to series by status
          var DISPLAY_STATUS = ['completed', 'busy', 'failed', 'no-answer', 'canceled', 'unknown'];
          series = _.map(DISPLAY_STATUS, function(status) { 
            var s = _.map(data.objects, function(value, date) {
              return [date, value[status]];
            });
            return {'name': status, 'data': s };
          });
          // chart as stacked columns
          var chartOpts = _.extend(self.chartOpts, {stacked: true});
          self.chart = new Chartkick.ColumnChart('chart_display', series, chartOpts);
        } else {
          // all calls for timespan
          // get campaigns.json to match series labels
          $.getJSON('/api/campaigns.json', function(campaigns) {
            series = _.map(campaigns.objects, function(campaign_name, campaign_id) {
              var s = _.map(data.objects, function(value, date) {
                if (value[campaign_id]) {
                  return [date, value[campaign_id]];
                }
              });
              // compact to remove falsy values
              return {'name': campaign_name, 'data': _.compact(s) };
            });
            // filter out series that have no data
            var seriesFiltered = _.filter(series, function(line) {
              return line.data.length
            });

            if (seriesFiltered.length) {
              // chart as curved lines
              var chartOpts = _.extend(self.chartOpts, {curve: true});
              self.chart = new Chartkick.LineChart('chart_display', seriesFiltered, chartOpts);
            } else {
              $('#chart_display').html('no data to display. adjust dates or campaigns');
            }

            if (data.meta) {
              $('#summary_data').html(
                self.summaryDataTemplate(data.meta)
              ).show();
            }
          });
        }
      });

      if (this.campaignId) {
        // table data for calls per target
        var tableDataUrl = '/api/campaign/'+this.campaignId+'/target_calls.json?';
        if (start) {
          tableDataUrl += ('&start='+start);
        }
        if (end) {
          tableDataUrl += ('&end='+end);
        }

        $('table#table_data').html('<span class="glyphicon glyphicon-refresh spin"></span> Loading...');
        $('#table_display').show();
        $.getJSON(tableDataUrl).success(function(data) {
          var content = self.targetDataTemplate(data.objects);
          return $('table#table_data').html(content).promise();
        }).then(function() {
          return $('table#table_data').tablesorter({
            theme: "bootstrap",
            headerTemplate: '{content} {icon}',
            headers: {
              1: {
                sorter:'lastname'
              }
            },
            sortList: [[3,1]],
            sortInitialOrder: "asc",
            widgets: [ "uitheme", "columns", "zebra", "output"],
            widgetOptions: {
              zebra : ["even", "odd"],
              output_delivery: 'download',
              output_saveFileName: 'callpower-export.csv'
            }
          }).promise();
        }).then(function() {
          $('.btn.download').show();
          // don't know why this is necessary, but it appears to be
          setTimeout(function() {
            $('table#table_data').trigger("updateAll");
          }, 10);
        });
      } else {
        $('#table_display').hide();
      }
    },

    downloadTable: function(event) {
      $('table#table_data').trigger('outputTable');
    },
  });
})();
/*global CallPower, Backbone */

(function () {
  CallPower.Views.SystemForm = Backbone.View.extend({
    el: $('#system'),

    events: {
      'click .reveal': 'toggleSecret',
    },

    toggleSecret: function(event) {
      var input = $(event.target).parent().siblings('input');
        if (input.prop('type') === 'password') {
            input.prop('type','text');
        } else {
            input.prop('type','password');
        }
    }

  });

})();
/*global CallPower, Backbone */

(function () {
  CallPower.Models.Target = Backbone.Model.extend({
    defaults: {
      id: null,
      uid: null,
      title: null,
      name: null,
      number: null,
      order: null
    },

  });

  CallPower.Collections.TargetList = Backbone.Collection.extend({
    model: CallPower.Models.Target,
    comparator: 'order'
  });

  CallPower.Views.TargetItemView = Backbone.View.extend({
    tagName: 'li',
    className: 'list-group-item target',

    initialize: function() {
      this.template = _.template($('#target-item-tmpl').html(), { 'variable': 'data' });
    },

    render: function() {
      var html = this.template(this.model.toJSON());
      this.$el.attr('id', 'target_set-'+this.model.get('order'));
      this.$el.html(html);
      return this;
    },

    events: {
      'keydown [contenteditable]': 'onEdit',
      'paste [contenteditable]': 'onEdit',
      'blur [contenteditable]': 'onSave',
      'click .remove': 'onRemove',
    },

    onEdit: function(event) {
      var target = $(event.target);
      var esc = (event.which === 27),
          nl = (event.which === 13),
          tab = (event.which === 9);

      if (esc) {
        document.execCommand('undo');
        target.blur();
      } else if (nl) {
        event.preventDefault(); // stop user from creating multi-line spans
        target.blur();
      } else if (tab) {
        event.preventDefault(); // prevent focus from going back to first field
        target.next('[contenteditable]').focus(); // send it to next editable
      } else if (target.text() === target.attr('placeholder')) {
        target.text(''); // overwrite placeholder text
        target.removeClass('placeholder');
      } else if (event.type==='paste') {
        setTimeout(function() {
          // on paste, convert html to plain text
          target.html(target.text());
        },10);
      }
    },

    onSave: function(event) {
      var field = $(event.target);

      if (field.text() === '') {
        // empty, reset to placeholder
        field.text(field.attr('placeholder'));
      }
      if (field.text() === field.attr('placeholder')) {
        field.addClass('placeholder');
        return;
      }

      var fieldName =field.data('field');
      this.model.set(fieldName, field.text());
      field.removeClass('placeholder');
    },

    onRemove: function(event) {
      // clear related inputs
      var sel = 'input[name^="target_set-'+this.model.get('order')+'"]';
      this.$el.remove(sel);

      // and destroy the model
      this.model.destroy();
    },

  });

  CallPower.Views.TargetList = Backbone.View.extend({
    el: '#set-targets',

    events: {
      'click .add': 'onAdd',
    },

    initialize: function() {
      this.collection = new CallPower.Collections.TargetList();
      // bind to future render events
      this.listenTo(this.collection, 'add remove sort reset', this.render);
      this.listenTo(this.collection, 'add', this.recalculateOrder);

      // make target-list items sortable
      $('.target-list.sortable').sortable({
         items: 'li',
         handle: '.handle',
      }).bind('sortupdate', this.onSortUpdate);
    },

    loadExistingItems: function() {
      // check for items in serialized inputs
      if(this.$el.find('input[name="target_set_length"]').val()) {
        this.deserialize();
        this.recalculateOrder(this);
      }
    },

    render: function() {
      var $list = this.$('ol.target-list').empty().show();

      var rendered_items = [];
      this.collection.each(function(model) {
        var item = new CallPower.Views.TargetItemView({
          model: model,
          attributes: {'data-cid': model.cid}
        });
        var $el = item.render().$el;

        _.each(model.attributes, function(val, key) {
          if (val === null) {
            // set text of $el, without triggering blur
            var sel = 'span[data-field="'+key+'"]';
            var span = $el.children(sel);
            var pl = span.attr('placeholder');
            span.text(pl).addClass('placeholder');
          }
        });

        rendered_items.push($el);
      }, this);
      $list.append(rendered_items);

      var target_set_errors = this.$el.find('input[name^="target_set-"]').filter('[name$="-error"]');
      target_set_errors.each(function(error) {
        var id = $(this).attr('name').replace('-error','');
        var item = $('#'+id);
        item.addClass('error');

        var message = $(this).val();
        item.append('<span class="message">'+message+'</span>');
      });

      $('.target-list.sortable').sortable('update');

      return this;
    },

    serialize: function() {
      // write collection to hidden inputs in format WTForms expects
      var target_set = this.$el.find('#target-set');

      // clear any existing target_set-N inputs
      target_set.find('input').remove('[name^="target_set-"]');

      this.collection.each(function(model, index) {
        // create new hidden inputs named target_set-N-FIELD
        var fields = ['order','title','name','number','uid'];
        _.each(fields, function(field) {
          var input = $('<input name="target_set-'+index+'-'+field+'" type="hidden" />');
          input.val(model.get(field));

          // append to target-set div
          target_set.append(input);
        });
      });
    },

    deserialize: function() {
      // destructive operation, create models from data in inputs
      var self = this;

      // clear rendered targets
      var $list = this.$('ol.target-list').empty();

      // figure out how many items we have
      var target_set_length = this.$el.find('input[name="target_set_length"]').val();

      // iterate over total
      var items = [];
      _(target_set_length).times(function(n) {
        var model = new CallPower.Models.Target();
        var fields = ['order','title','name','number','uid'];
        _.each(fields, function(field) {
          // pull field values out of each input
          var sel = 'input[name="target_set-'+n+'-'+field+'"]';
          var val = self.$el.find(sel).val();
          model.set(field, val);
        });
        items.push(model);
      });
      self.collection.reset(items);
    },

    shortRandomString: function(prefix, length) {
      // generate a random string, with optional prefix
      // should be good enough for use as uid
      if (length === undefined) { length = 6; }
      var randstr = ((Math.random()*Math.pow(36,length) << 0).toString(36)).slice(-1*length);
      if (prefix !== undefined) { return prefix+randstr; }
      return randstr;
    },

    onAdd: function() {
      // create new empty item
      var item = this.collection.add({
        uid: this.shortRandomString('custom:', 6),
        order: this.collection.length
      });
      this.recalculateOrder(this);
    },

    onSortUpdate: function() {
      // because this event is bound by jQuery, 'this' is the element, not the parent view
      var view = CallPower.campaignForm.targetListView; // get a reference to it manually
      return view.recalculateOrder(); // pass it to the backbone view
    },

    recalculateOrder: function() {
      var self = this;
      // iterate over DOM objects to set item order
      $('.target-list .list-group-item').each(function(index) {
        var elem = $(this); // in jquery.each, 'this' is the element
        var cid = elem.data('cid');
        var item = self.collection.get(cid);
        if(item) { item.set('order', index); }
      });
    },

  });

})();
/*global CallPower, Backbone */

(function () {
  CallPower.Models.AudioRecording = Backbone.Model.extend({
    defaults: {
      id: null,
      key: null,
      description: null,
      version: null,
      hidden: null,
      campaign_ids: null,
      selected_campaign_ids: null,
      file_url: null,
      text_to_speech: null
    },

  });

  CallPower.Collections.AudioRecordingList = Backbone.Collection.extend({
    model: CallPower.Models.AudioRecording,
    url: '/api/audiorecording',
    comparator: 'version',

    initialize: function(key, campaign_id) {
      this.key = key;
      this.campaign_id = campaign_id;
    },

    parse: function(response) {
      return response.objects;
    },

    fetch: function(options) {
      // do specific pre-processing for server-side filters
      // always filter on AudioRecording key
      var keyFilter = [{name: 'key', op: 'eq', val: this.key}];
      var flaskQuery = {
        q: JSON.stringify({ filters: keyFilter })
      };
      var fetchOptions = _.extend({ data: flaskQuery }, options);

      return Backbone.Collection.prototype.fetch.call(this, fetchOptions);
    }
  });

  CallPower.Views.RecordingItemView = Backbone.View.extend({
    tagName: 'tr',

    events: {
      'click button.select': 'onSelect',
      'click button.delete': 'onDelete',
      'click button.undelete': 'onUnDelete',
      'mouseenter button.select': 'toggleSuccess',
      'mouseleave button.select': 'toggleSuccess',
      'mouseenter button.delete': 'toggleDanger',
      'mouseleave button.delete': 'toggleDanger',
      'mouseenter button.undelete': 'toggleWarning',
      'mouseleave button.undelete': 'toggleWarning',
    },

    initialize: function() {
      this.template = _.template($('#recording-item-tmpl').html(), { 'variable': 'data' });
    },

    render: function() {
      var data = this.model.toJSON();
      data.campaign_id = parseInt(this.model.collection.campaign_id);
      var html = this.template(data);
      this.$el.html(html);
      return this;
    },

    toggleSuccess: function(event) {
      $(event.target).toggleClass('btn-success');
    },

    toggleDanger: function(event) {
      $(event.target).toggleClass('btn-danger');
    },

    toggleWarning: function(event) {
      $(event.target).toggleClass('btn-warning');
    },

    onSelect: function(event) {
      this.model.collection.trigger('select', this.model.attributes);
    },

    onDelete: function(event) {
      this.model.collection.trigger('delete', this.model.attributes);
    },

    onUnDelete: function(event) {
      this.model.collection.trigger('undelete', this.model.attributes);
    },

  });

  CallPower.Views.VersionsModal = Backbone.View.extend({
    tagName: 'div',
    className: 'versions modal fade',

    events: {
      'change input.filter': 'onFilterCampaigns'
    },

    initialize: function(viewData) {
      this.template = _.template($('#recording-modal-tmpl').html(), { 'variable': 'modal' });
      _.bindAll(this, 'destroyViews');

      this.viewData = viewData;
      this.collection = new CallPower.Collections.AudioRecordingList(this.viewData.key, this.viewData.campaign_id);
      this.filteredCollection = new FilteredCollection(this.collection);
      this.collection.fetch({ reset: true });
      this.views = [];

      this.listenTo(this.collection, 'reset add remove', this.renderFilteredCollection);
      this.listenTo(this.filteredCollection, 'filtered:reset filtered:add filtered:remove', this.renderFilteredCollection);
      this.listenTo(this.collection, 'select', this.selectVersion);
      this.listenTo(this.collection, 'delete', this.deleteVersion);
      this.listenTo(this.collection, 'undelete', this.unDeleteVersion);

      this.$el.on('hidden.bs.modal', this.destroyViews);
    },

    render: function() {
      // render template
      var html = this.template(this.viewData);
      this.$el.html(html);

      // reset initial filters
      this.onFilterCampaigns();

      // show the modal
      this.$el.modal('show');

      return this;
    },

    renderFilteredCollection: function() {
      var self = this;

      // clear any existing subviews
      this.destroyViews();
      var $list = this.$('table tbody').empty();

      // create subviews for each item in collection
      this.views = this.filteredCollection.map(this.createItemView, this);
      $list.append( _.map(this.views,
        function(view) { return view.render(self.campaign_id).el; },
        this)
      );
    },

    destroyViews: function() {
      // destroy each subview
      _.invoke(this.views, 'destroy');
      this.views.length = 0;
    },

    hide: function() {
      this.$el.modal('hide');
    },

    createItemView: function (model) {
      return new CallPower.Views.RecordingItemView({ model: model });
    },

    onFilterCampaigns: function() {
      var self = this;

      var showAllCampaigns = ($('input.filter[name=show_all_campaigns]:checked', this.$el).length > 0);
      var showHidden = ($('input.filter[name=show_hidden]:checked', this.$el).length > 0);

      if (showAllCampaigns) {
        this.filteredCollection.removeFilter('campaign_id');
      } else {
        this.filteredCollection.filterBy('campaign_id', function(model) {
          return _.contains(model.get('campaign_ids'), parseInt(self.viewData.campaign_id));
        });
      }
      if (showHidden) {
        this.filteredCollection.removeFilter('hidden');
      } else {
        this.filteredCollection.filterBy('hidden', function(model) {
          return (model.get('hidden') !== true); // show only those not hidden
        });
      }
    },

    ajaxPost: function(data, endpoint, hideOnComplete) {
      // make ajax POST to API
      var url = '/admin/campaign/'+this.viewData.campaign_id+'/audio/'+data.id+'/'+endpoint;
      var self = this;
      $.ajax({
        url: url,
        method: 'POST',
        success: function(response) {
          if (response.success) {
              // build friendly message like "Audio recording selected: Introduction version 3"
              var fieldDescription = $('form label[for="'+response.key+'"]').text();
              var msg = response.message + ': '+ fieldDescription + ' version ' + response.version;
              // and display to user
              window.flashMessage(msg, 'success');

              // close the modal, and cleanup subviews
              if (hideOnComplete) {
                self.hide();
              }
            } else {
              console.error(response);
              window.flashMessage(response.errors, 'error', true);
            }
        }, error: function(xhr, status, error) {
          console.error(status, error);
          window.flashMessage(response.errors, 'error');
        }
      });
    },

    selectVersion: function(data) {
      return this.ajaxPost(data, 'select', true);
    },

    deleteVersion: function(data) {
      // TODO, confirm with user
      // this doesn't actually delete objects in database or on file system
      // just hides from API

      return this.ajaxPost(data, 'hide');
    },

    unDeleteVersion: function(data) {
      return this.ajaxPost(data, 'show');
    }

  });
})();