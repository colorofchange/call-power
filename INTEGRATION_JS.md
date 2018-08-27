
Embedding Javascript
===========

Campaigns can be easily embedded in external forms by including `<script src="/api/campaign/ID/embed.js"></script>`. 
This script loads jQuery from a CDN (if not already available), and attaches a post-submit callback to the specified form.

Additional parameters can be specified on the `CallPowerOptions` object before inserting the script:

* form: form id to attach, defaults to 'call_form'
* phoneField: input id with the user phone number, defaults to 'phone_id'
* locationField: input id with the user location, defaults to 'location_id'
* scriptDisplay: one of 'replace', 'redirect', or 'overlay'
* if scriptDisplay is 'redirect', redirectAfter will set the new URL
* if scriptDisplay is 'overlay', overlayCloseText: will add a link below the responseText
* if errorTracking is defined, errors will be reported to the SENTRY_DSN public endpoint via Raven.js

To render a complete form, include `<iframe src="/api/campaign/ID/embed_iframe.html"></iframe>">` to create a form ready to be filled out.

Custom Embeds
-------------

The embed script should interoperate with existing forms, but if you have a form with a submit callback already defined, you may want to write your own integration. You can add javascript that will be run after the success callback in the Custom JS field. For example, if you are using the overlay script display, you might want to manually trigger an action after the overlay is closed, like `$('.overlay').on('hide', function() { actionkit.form.submit(); });`

If your validation needs are more complex, you can include just CallPowerForm.js from `/api/campaign/ID/CallPowerForm.js` and define your own functions for location, phone, onSuccess or onError.

Calling Endpoints Directly
--------------------------

You can also trigger a phone call by hitting the `/call/create` endpoint directly with either a GET or a POST. URL parameters should include:

* userPhone (required)
* campaignId (required)
* userLocation (optional)
* userCountry (optional)
* ref (optional, limited to 64 characters)

The response will be a JSON object with the following fields:

```
{
  "call": "queued", 
  "campaign": "live", "paused", or "archived", 
  "fromNumber": "+18005551212", 
  "redirect": null or a URL to redirect to on success, 
  "script": "" or an HTML blob to display to the user, 
  "targets": {
    "segment": "custom",
    "objects": [
      {
        "name": "", 
        "phone": "", 
        "title": ""
      }, 
    ]
    or "display": "Congress" (a string to display for campaigns which do not have pre-set custom targets)
}
```