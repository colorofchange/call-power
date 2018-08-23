/*global CallPower, Backbone */

(function () {
  CallPower.Views.SystemForm = Backbone.View.extend({
    el: $('#system'),

    events: {
      'click .reveal': 'toggleSecret',
      'submit form.crm-sync': 'syncSubmit',
    },

    toggleSecret: function(event) {
      var input = $(event.target).parent().siblings('input');
        if (input.prop('type') === 'password') {
            input.prop('type','text');
        } else {
            input.prop('type','password');
        }
    },

    syncSubmit: function(event) {
      event.preventDefault();
      var form = $(event.target);
      if (form.hasClass('disabled')) {
        return false;
      }

      $.ajax({
        url: form.attr('action'),
        method: 'POST',
        success: function(response) {
          if (response.scheduled_start_time) {
            console.log('starting at', response.scheduled_start_time);
            // put it in the right table cell, disable the button
            $(form).siblings('.last_sync_time').text(response.scheduled_start_time);
            $(form).addClass('disabled');
            $(form).find('button[type="submit"]').addClass('disabled');
          };
        }
      });
    }
  });

})();