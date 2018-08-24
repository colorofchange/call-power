from datetime import datetime

from flask import current_app

from ..extensions import db, rq

from ..call.models import Call
from ..campaign.models import Campaign

class SyncCampaign(db.Model):
    __tablename__ = 'sync_campaign'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36)) # UUID4
    created_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_sync_time = db.Column(db.DateTime)

    campaign_id = db.Column(db.ForeignKey('campaign_campaign.id'))
    campaign = db.relationship('Campaign', backref=db.backref('sync_campaign', lazy='dynamic'))

    crm_id = db.Column(db.String(40)) # id of the campaign in the CRM

    def __init__(self, campaign_id, crm_id):
        self.campaign_id = campaign_id
        self.crm_id = crm_id
        self.start()
        db.session.add(self)    
        db.session.commit()

    def start(self, location=None):
        crontab = '{minute} {hour} {day_of_month} {month} {days_of_week}'.format(
            minute=0,
            hour='*',
            day_of_month='*',
            month='*',
            days_of_week='*')
        from jobs import sync_campaigns
        cron_job = sync_campaigns.cron(crontab, 'sync:sync_campaigns:{}'.format(self.campaign_id), self.campaign_id)
        self.job_id = cron_job.id

    def stop(self):
        rq.get_scheduler().cancel(self.job_id)

    def sync_calls(self, integration):
        unsynced_calls = Call.query.filter_by(campaign=self.campaign, sync_call=None)
        for call in unsynced_calls:
            sync_call = SyncCall(call.id)
            result = sync_call.save_to_crm(self, integration)
            if result:
                db.session.add(sync_call)

        completed_calls = Call.query.filter_by(campaign=self, status='completed')
        integration.save_campaign_meta(self.crm_id, {'count': completed_calls.count()})
        self.last_sync_time = datetime.utcnow()
        db.session.add(self)    
        db.session.commit()


class SyncCall(db.Model):
    __tablename__ = 'sync_call'

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime, default=datetime.utcnow)

    call_id = db.Column(db.ForeignKey('calls.id'))
    call = db.relationship('Call', backref=db.backref('sync_call', lazy='dynamic'))

    saved = db.Column(db.Boolean, default=False)

    def __init__(self, call_id):
        self.call_id = call_id
        self.call = Call.query.get(self.call_id)

    def save_to_crm(self, sync_campaign, integration):
        # we only keep a hash of the phone locally, for privacy
        # so hit twilio to get the actual phone to match to the CRM
        
        if self.call:
            twilio_sid = self.call.call_id
            user_phone = integration.get_phone(twilio_sid)
        else:
            current_app.logger.warning('unable to get twilio_sid for call: %s' % self.call)
            return False

        if not user_phone:
            current_app.logger.warning('unable to get user_phone for twilio_sid: %s' % twilio_sid)
            return False

        crm_user = integration.get_user(user_phone)
        current_app.logger.info('got user %s' % crm_user['id'])
        if not crm_user:
            current_app.logger.warning('unable to get crm user for phone: %s' % user_phone)
            return False

        self.saved = integration.save_action(self.call, sync_campaign.crm_id, crm_user)
        current_app.logger.info('synced %s->%s' % (crm_user['id'], self.call.id))
        return True
