from flask import current_app
import requests

class CRMIntegration(object):

    def __init__(self, *args, **kwargs):
        self.twilio_client = current_app.config['TWILIO_CLIENT']

    def get_phone(self, twilio_sid):
        """Gets the dialed phone for a Session from Twilio in e164 format"""
        twilio_call = self.twilio_client.calls.get(twilio_sid)
        return twilio_call.to

    def get_user(self, phone_number):
        """Gets a user from the CRM with the given phone number
        Returns a unique ID, implementation dependent"""
        raise NotImplementedError()

    def save_action(self, sync_call, crm_campaign_id, crm_user_id):
        """Given a sync_call, crm_campaign and crm_user
        Save the call attributes (target, duration and status) to the CRM
        Returns a boolean status"""
        raise NotImplementedError()

    def save_campaign_meta(self, crm_campaign_id, meta):
        """Given a crm_campaign
        Save aggregate call counts to the CRM
        Returns a boolean status"""
        raise NotImplementedError()

class CRMIntegrationError(Exception):
    def __init__(self, message):
        self.message = message

