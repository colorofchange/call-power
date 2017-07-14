from flask import url_for
import requests

from ..utils import utc_now
from ..extensions import db, rq


class ScheduleCall(db.Model):
    # tracks outbound calls to target
    __tablename__ = 'schedule_call'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True))
    subscribed = db.Column(db.Boolean, default=True)

    time_to_call = db.Column(db.Time()) # should be UTC
    last_called  = db.Column(db.DateTime(timezone=True))
    num_calls = db.Column(db.Integer, default=0)

    campaign_id = db.Column(db.ForeignKey('campaign_campaign.id'))
    campaign = db.relationship('Campaign')

    phone_number = db.Column(db.String(16))  # number to call, e164

    job_id = db.Column(db.String(36)) # UUID4

    def __init__(self, campaign_id, phone_number, time=utc_now().time()):
        self.created_at = utc_now()
        self.campaign_id = campaign_id
        self.phone_number = phone_number
        self.time_to_call = time

    def __repr__(self):
        return u'<ScheduleCall for {} to {}>'.format(self.campaign.name, self.phone_number)

    @property
    def _function_name(self):
        return 'create_call:{campaign_id}:{phone}'.format(campaign_id=self.campaign_id, phone=self.phone_number)


    def start_job(self, location=None):
        self.subscribed = True
        weekdays = 'mon,tue,wed,thu,fri'
        minute = self.time_to_call.minute
        hour = self.time_to_call.hour
        # TODO, set a max limit on the number of executions?
        crontab = '{minute} {hour} {day_of_month} {month} {days_of_week}'.format(
            minute=minute,
            hour=hour,
            day_of_month='*',
            month='*',
            days_of_week=weekdays)
        cron_job = create_call.cron(crontab, self._function_name, self.campaign_id, self.phone_number, location)
        self.job_id = cron_job.id

    def stop_job(self):
        self.subscribed = False
        rq.get_scheduler().cancel(self.job_id)

@rq.job
def create_call(campaign_id, phone, location):
    params = {
        'campaignId': campaign_id,
        'userPhone': phone,
        'userLocation': location
    }
    scheduled_call = ScheduleCall.query.filter_by(campaign_id=campaign_id, phone_number=phone).first()
    resp = requests.get(url_for('call.create', _external=True, **params))
    if resp.status_code == 200:
        scheduled_call.num_calls += 1
        scheduled_call.last_called = utc_now()
        db.session.add(scheduled_call)
        db.session.commit()
        return True
    else:
        current_app.logger.error('unable to execute scheduled create_call: %s "%s"' % (resp.url, resp.content))
        return False