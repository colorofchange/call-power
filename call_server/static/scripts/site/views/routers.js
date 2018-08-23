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
      "campaign/:id/schedule": "scheduleLog",
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

    scheduleLog: function(id) {
      CallPower.scheduleLog = new CallPower.Views.ScheduleLog(id);
    },

    systemForm: function() {
      CallPower.systemForm = new CallPower.Views.SystemForm();
    },

    statisticsView: function() {
      CallPower.statisticsView = new CallPower.Views.StatisticsView();
    }
  });
})();