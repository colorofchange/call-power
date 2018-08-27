from flask import current_app

import requests
from . import CRMIntegration
from actionkit.rest import ActionKit
from actionkit.xmlrpc import ActionKitXML
import phonenumbers

class ActionKitIntegration(CRMIntegration):

    def __init__(self, domain, username, api_key=None, password=None):
        super(ActionKitIntegration, self).__init__()
        if api_key:
            self.ak_client = ActionKit(instance=domain, username=username, api_key=api_key)
            self.ak_rpc = ActionKitXML(instance=domain, username=username, api_key=api_key)
        elif password:
            self.ak_client = ActionKit(instance=domain, username=username, password=password)
            self.ak_rpc = ActionKitXML(instance=domain, username=username, password=password)
        else:
            raise Exception('unable to authenticate to ActionKit')

    def get_user(self, phone_number):
        """Gets a user from ActionKit with the given phone number
        Returns user dict"""

        # "normalize" the actionkit way
        # remove e164 formatting and use national_number
        normalized_phone = phonenumbers.parse(phone_number).national_number

        matching_users = self.ak_client.phone.list(normalized_phone=normalized_phone)['objects']
        if len(matching_users) > 0:
            user_url = matching_users[0]['user']
            ak_user = self.ak_client.get(user_url)
            # store phone in there, because there's no direct link
            ak_user['phone'] = str(normalized_phone)
            return ak_user
        else:
            return None

    def _match_ak_target_data(self, campaign, target):
        """Look up a target in our political_data cache
        Returns a tuple to match actionkit's target.type and state values"""
        target_type = None
        target_state = None

        if campaign.country_code.upper() == 'US':
            # look up target in political_data
            data_provider = campaign.get_country_data()
            target_data = data_provider.cache_get(target_key)
            
            if campaign.campaign_type == 'congress':
                target_state = target_data.get('state', '')

                if target.title == 'Senator':
                    target_type = 'senate'
                elif target.title == 'Representative':
                    target_type = 'house'

            elif target.title == 'Governor':
                target_type = 'governor'
                # TODO governor target_state

        if campaign.country_code.upper() == 'CA':
            if campaign.campaign_type == 'lower':
                target_type = 'parliament'

        if not target_type:
            target_type = 'other'
        if not target_state:
            target_state = ''

        return (campaign.country_code, target_state, target_type, target.name)


    def _get_target_id(self, country, state, target_type, target_name):
        """Gets a target from ActionKit in the given country, state, type (senate, house, custom), and first/last name
        Returns a target ID"""

        # match in actionkit by country, state and type
        # these are the only indexed fields
        target_data = {'country': country,
                       'state': state,
                       'type': target_type}
        ak_targets_list = self.ak_client.target.list(**target_data)['objects']

        # check list of possible matches from actionkit by first+last name
        first_name, last_name = target_name.split(' ')
        ak_target = None
        for t in ak_targets_list:
            if t['last'] == last_name and t['first'] == first_name:
                ak_target = t
                current_app.logger.info("found target: %s" % target_name) 
        if not ak_target:
            # it doesn't exist, create it
            target_data['last'] = last_name
            target_data['first'] = first_name
            if target_type == 'parliament':
                target_data['title'] = 'MP'
            if target_type == 'governor':
                target_data['title'] = 'Governor'
            current_app.logger.info("creating target: %s" % target_data)
            ak_target = self.ak_client.target.create(target_data)
        return ak_target['id']


    def save_action(self, call, crm_campaign_id, crm_user):
        """Given a sync_call, crm_campaign and crm_user
        Save the call attributes (target, duration and status) to the CRM
        Returns a boolean status"""
        
        ak_target_data = self._match_ak_target_data(call.campaign, call.target)
        crm_target_id = self._get_target_id(*ak_target_data)

        # create the call action
        call_action = {
            'email': crm_user['email'],
            'phone': crm_user['phone'],
            'page': crm_campaign_id,
            'source': 'CallPower CRMSync',
            'target_checked': crm_target_id,
            'action_duration': call.duration,
            'action_status': call.status,
            'skip_confirmation': 1,
        }
        current_app.logger.info("creating action: %s" % call_action) 
        ak_callaction = self.ak_client.action.create(call_action)
        return True


    def save_campaign_meta(self, crm_campaign_id, meta={}):
        """Given a page name (crm_campaign_id) 
        Save meta values to pagefields
        Returns a boolean status"""

        # get page id via REST API
        response = self.ak_client.get('/rest/v1/page/', params={'name': crm_campaign_id})
        campaign_page = response['objects'][0]

        page_custom_fields = {}
        # and set custom fields via XMLRPC
        for (key, value) in meta.items():
            name = 'callpower_{}'.format(key) # namespace custom field name
            page_custom_fields[name] = value
        page_custom_fields['id'] = campaign_page['id']            

        xml_response = self.ak_rpc.Page.set_custom_fields(page_custom_fields)

        # check at least the last custom page field got set
        if xml_response.get(name) == value:
            return True
        else:
            current_app.logger.info("unable to update pagefield: {} for {}".format(name, crm_campaign_id)) 
            return False
        return True
