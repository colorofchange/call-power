import hashlib
from datetime import datetime
import pytz

from ..extensions import db
from ..utils import utc_now

from sqlalchemy_utils.types import phone_number

class Blocklist(db.Model):
    # stops
    __tablename__ = 'admin_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True))
    expires = db.Column(db.Interval)
    phone_number = db.Column(phone_number.PhoneNumberType(), nullable=True)
    phone_hash = db.Column(db.String(64), nullable=True) # hashed phone number (optional)
    ip_address = db.Column(db.String(16), nullable=True)
    hits = db.Column(db.Integer(), default=0)

    def __init__(self, phone_number=None, ip_address=None):
        self.timestamp = utc_now()
        self.phone_number = phone_number
        self.ip_address = ip_address

    def __unicode__(self):
        if self.phone_number:
            return self.phone_number.__unicode__()
        if self.phone_hash:
            return self.phone_hash
        if self.ip_address:
            return  self.ip_address


    def is_active(self):
        if self.expires:
            try:
                return utc_now() <= (self.timestamp + self.expires)
            except TypeError:
                # sqlite doesn't store timezones in the database
                # reset it manually
                aware_timestamp = self.timestamp.replace(tzinfo=pytz.utc)
                return utc_now() <= (aware_timestamp + self.expires)
        else:
            return True

    def match(self, user_phone, user_ip, user_country='US'):
        if self.ip_address:
            return self.ip_address == user_ip
        if self.phone_hash:
            return self.phone_hash == hashlib.sha256(user_phone).hexdigest()
        if self.phone_number:
            return self.phone_number == phone_number.PhoneNumber(user_phone, user_country)
        
    @classmethod
    def active_blocks(cls):
        return [b for b in Blocklist.query.all() if b.is_active()]

    @classmethod
    def user_blocked(cls, user_phone, user_ip, user_country='US'):
        """
        Takes a phone number and/or IP address, check it against blocklist
        """
        active_blocks = cls.active_blocks()
        if not active_blocks:
            # exit early if no blocks active
            return False

        matched = False
        for b in active_blocks:
            if b.match(user_phone, user_ip, user_country):
                if not b.phone_number:
                    b.phone_number = user_phone
                matched = True
                b.hits += 1
                db.session.add(b)

        if matched:
            db.session.commit()
        return matched

