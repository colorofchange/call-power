from flask import current_app

from ..extensions import db, rq

from .models import SyncCampaign
from .integrations import CRMIntegrationError

def get_crm_integration():
    # setup integration from config values
    if current_app.config['CRM_INTEGRATION'] == 'ActionKit':
        from .integrations.actionkit_crm import ActionKitIntegration
        ak_credentials = {'domain': current_app.config['ACTIONKIT_DOMAIN'],
                          'username': current_app.config['ACTIONKIT_USER']}
        if 'ACTIONKIT_PASSWORD' in current_app.config:
            ak_credentials['password'] = current_app.config['ACTIONKIT_PASSWORD']
        elif 'ACTIONKIT_API_KEY' in current_app.config:
            ak_credentials['api_key'] = current_app.config['ACTIONKIT_API_KEY']
        else:
            raise CRMIntegrationError('either ACTIONKIT_API_KEY or ACTIONKIT_PASSWORD must be configured')
        crm_integration = ActionKitIntegration(**ak_credentials)
    else:
        raise CRMIntegrationError('no CRM_INTEGRATION configured')
        return False
    return crm_integration


@rq.job
def sync_campaigns(campaign_id='all'):
    crm_integration = get_crm_integration()

    if campaign_id_list == 'all':
        campaigns_to_sync = SyncCampaign.query.all()
    else:
        campaigns_to_sync = SyncCampaign.query.filter_by(campaign_id=campaign_id)

    for sync_campaign in campaigns_to_sync:
        current_app.logger.info('sync campaign ID: %s' % sync_campaign.campaign_id)
        sync_campaign.sync_calls(crm_integration)