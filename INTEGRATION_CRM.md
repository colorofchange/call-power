CRM Integrations
===========

CallPower is designed to keep as little data as required to place calls connecting their members to targets. However, it can be useful for some organizations to track the duration of individual calls, to identify conversations that may be useful for staff to follow-up.

An out-of-band sync system copies call information to a CRM, joining user records on their phone number or other unique ID, and storing the duration of the call, which target(s) they were connected to, and the overall status of their call session.

This is run nightly with rq jobs, which requires running a scheduler and at least one worker.

Configuration
----

ActionKit

- `CRM_INTEGRATION=ActionKit`
- `ACTIONKIT_DOMAIN=client.actionkit.com`
- `ACTIONKIT_USER`
- `ACTIONKIT_PASSWORD` or `ACTIONKIT_API_KEY`