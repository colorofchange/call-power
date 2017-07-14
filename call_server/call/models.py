import hashlib
from datetime import datetime

from ..extensions import db

from .constants import STRING_LEN


class Call(db.Model):
    # tracks outbound calls to target
    __tablename__ = 'calls'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True))

    # session
    session_id = db.Column(db.ForeignKey('calls_session.id'))
    session = db.relationship('Session', backref=db.backref('calls'))

    # campaign
    campaign_id = db.Column(db.ForeignKey('campaign_campaign.id'))
    campaign = db.relationship('Campaign')

    # target
    target_id = db.Column(db.ForeignKey('campaign_target.id'))
    target = db.relationship('Target')

    # twilio attributes
    call_id = db.Column(db.String(40))    # twilio call ID
    status = db.Column(db.String(25))     # twilio call status
    duration = db.Column(db.Integer)      # twilio call time in seconds

    def __init__(self, session_id, campaign_id, target_id, call_id=None, status='unknown', duration=0):
        self.timestamp = datetime.utcnow()
        self.session_id = session_id
        self.campaign_id = campaign_id
        self.target_id = target_id
        self.call_id = call_id
        self.status = status
        self.duration = duration

    def __repr__(self):
        return u'<Call to {}>'.format(self.target.name)

    def target_display(self):
        if self.target:
            return self.target.full_name()


class Session(db.Model):
    # tracks calls session by user for a campaign
    __tablename__ = 'calls_session'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True))

    # campaign
    campaign_id = db.Column(db.ForeignKey('campaign_campaign.id'))
    campaign = db.relationship('Campaign')

    # user attributes
    phone_hash = db.Column(db.String(64), nullable=True)  # hashed phone number (optional)
    location = db.Column(db.String(STRING_LEN))  # provided location

    # twilio attributes
    from_number = db.Column(db.String(16))  # campaign call number, e164
    twilio_id = db.Column(db.String(40))    # twilio call ID
    duration = db.Column(db.Integer)        # twilio call time in seconds
    status = db.Column(db.String(25))       # session status (initiated, completed, failed)

    direction = db.Column(db.String(25))    # (inbound, outbound)
    queue_delay = db.Column(db.Interval)  # difference between timestamp and ringing event

    @classmethod
    def hash_phone(cls, number):
        """
        Takes a phone number and returns a 64 character string
        """
        return hashlib.sha256(number).hexdigest()

    def __init__(self, campaign_id, phone_number=None, location=None, from_number=None, status='initiated', direction='outbound'):
        self.timestamp = datetime.utcnow()
        self.campaign_id = campaign_id
        if phone_number:
            self.phone_hash = self.hash_phone(phone_number)
        self.location = location
        self.from_number = from_number
        self.status = status
        self.direction = direction

    def __repr__(self):
        return u'<Session for {}>'.format(self.phone_hash)
