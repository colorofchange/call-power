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