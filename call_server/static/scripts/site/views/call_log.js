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