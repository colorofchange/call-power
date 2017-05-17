from datetime import datetime

from flask import current_app, url_for
from sqlalchemy_utils.types import phone_number, JSONType
from flask_store.sqla import FlaskStoreType
from sqlalchemy import UniqueConstraint

from ..extensions import db, cache
from ..utils import convert_to_dict
from ..political_data.adapters import adapt_by_key
from ..political_data import get_country_data
from .constants import (
    STRING_LEN,
    TWILIO_SID_LENGTH,
    LANGUAGE_CHOICES,
    CAMPAIGN_STATUS,
    STATUS_PAUSED,
    SEGMENT_BY_CHOICES,
    LOCATION_CHOICES,
    TARGET_OFFICE_CHOICES,
)


class Campaign(db.Model):
    __tablename__ = 'campaign_campaign'

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime, default=datetime.utcnow)

    name = db.Column(db.String(STRING_LEN), nullable=False, unique=True)
    country_code = db.Column(db.String(STRING_LEN), index=True)
    campaign_type = db.Column(db.String(STRING_LEN))
    campaign_state = db.Column(db.String(STRING_LEN))
    campaign_subtype = db.Column(db.String(STRING_LEN))
    campaign_language = db.Column(db.String(STRING_LEN))

    org_type = db.Column(db.String(STRING_LEN))
    tags = db.Column(db.Text)

    segment_by = db.Column(db.String(STRING_LEN))
    locate_by = db.Column(db.String(STRING_LEN))
    target_set = db.relationship('Target', secondary='campaign_target_sets',
                                 order_by='campaign_target_sets.c.order',
                                 backref=db.backref('campaigns'))
    target_ordering = db.Column(db.String(STRING_LEN))
    target_offices = db.Column(db.String(STRING_LEN))

    allow_call_in = db.Column(db.Boolean, default=False)
    phone_number_set = db.relationship('TwilioPhoneNumber', secondary='campaign_phone_numbers',
                                       backref=db.backref('campaigns'))
    call_maximum = db.Column(db.SmallInteger, nullable=True)

    audio_recordings = db.relationship('AudioRecording', secondary='campaign_audio_recordings',
                                       backref=db.backref('campaigns'))

    status_code = db.Column(db.SmallInteger, default=STATUS_PAUSED)

    embed = db.Column(JSONType)

    @property
    def status(self):
        return CAMPAIGN_STATUS.get(self.status_code, '')

    def __unicode__(self):
        return self.name

    def audio(self, key):
        return self.audio_or_default(key)[0]

    def has_audio(self, key='msg_intro'):
        # returns True if the campaign has non-default audio defined
        # False if not
        return not self.audio_or_default(key)[1]

    def audio_or_default(self, key):
        """Convenience method for getting selected audio recordings for this campaign by key.
        Returns tuple (audio recording or default message, is default message) """
        campaignAudio = self._audio_query().filter(
            CampaignAudioRecording.recording.has(key=key)
        ).first()

        if campaignAudio:
            return (campaignAudio.recording, False)
        else:
            # if not defined by user, return default
            return (current_app.config.CAMPAIGN_MESSAGE_DEFAULTS.get(key), True)

    def audio_msgs(self):
        "Convenience method for getting all selected audio recordings for this campaign"
        table = {}
        for r in self._audio_query().all():
            if r.recording.text_to_speech:
                table[r.recording.key] = r.recording.text_to_speech
            else:
                table[r.recording.key] = r.recording.file_url()
        return table

    def _audio_query(self):
        return CampaignAudioRecording.query.filter(
            CampaignAudioRecording.campaign_id == self.id,
            CampaignAudioRecording.selected == True)

    def campaign_type_display(self):
        "Display method for this campaign's type"
        campaign_data = self.get_campaign_data()
        if campaign_data:
            return campaign_data.type_name
        else:
            return None

    def campaign_subtype_display(self):
        "Display method for this campaign's subtype"
        campaign_data = self.get_campaign_data()
        if campaign_data:
            return campaign_data.get_subtype_display(self.campaign_subtype, campaign_region=self.campaign_state)
        else:
            return None

    @property
    def language_code(self):
        if self.campaign_language and self.country_code:
            return u"{}-{}".format(self.campaign_language.lower(), self.country_code.upper())
        else:
            return u"en-US"

    def language_display(self):
        return dict(LANGUAGE_CHOICES).get(self.campaign_language, '?')

    def order_display(self):
        "Display method for this campaign's ordering"
        campaign_data = self.get_campaign_data()
        if campaign_data:
            return campaign_data.get_order_display(self.target_ordering)
        else:
            return None

    def phone_numbers(self, region_code=None):
        "Phone numbers for this campaign, can be limited to a specified region code (ISO-2)"
        if region_code:
            # convert region_code to country_code for comparison
            country_code = phone_number.phonenumbers.country_code_for_region(region_code.upper())
            return [n.number.e164 for n in self.phone_number_set if n.number.country_code == country_code]
        else:
            # return all numbers in set
            return [n.number.e164 for n in self.phone_number_set]

    def required_fields(self):
        """API convenience method for rendering campaigns externally
        Returns dict of parameters and data types required to place call"""
        fields = dict()
        fields['userPhone'] = self.country_code
        if self.segment_by == 'location':
            fields['userLocation'] = self.locate_by
        return fields

    def segment_display(self):
        "Display method for this campaign's segmenting and locating of callers"
        val = dict(SEGMENT_BY_CHOICES).get(self.segment_by, '')
        if self.segment_by == 'location':
            val = '%s - %s' % (val, dict(LOCATION_CHOICES).get(self.locate_by))
        return val

    def targets(self):
        "Convenience method for getting list of target names and phone numbers"
        return [(t.name, t.number.e164) for t in self.target_set]

    def targets_display(self):
        "Display method for this campaign's target list if specified, or subtype (like Congress - Senate)"
        if self.target_set:
            return ", ".join(["%s" % t.name for t in self.target_set])
        else:
            return self.campaign_subtype_display()

    def target_offices_display(self):
        "Display method for this campaign's target offices"
        val = dict(TARGET_OFFICE_CHOICES).get(self.target_offices, '')
        return val

    @staticmethod
    def get_campaign_type_choices(country_code, cache=cache):
        country_data = get_country_data(country_code, cache=cache, api_cache='localmem')
        return country_data.campaign_type_choices

    def get_country_data(self, cache=cache):
        return get_country_data(self.country_code, cache=cache, api_cache='localmem')

    def get_campaign_data(self, cache=cache):
        country_data = self.get_country_data(cache)
        return country_data.get_campaign_type(self.campaign_type)


class CampaignTarget(db.Model):
    __tablename__ = 'campaign_target_sets'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign_campaign.id'))
    target_id = db.Column(db.Integer, db.ForeignKey('campaign_target.id'))
    order = db.Column(db.Integer())

    campaign = db.relationship('Campaign', backref='campaign_targets')
    target = db.relationship('Target', backref='campaign_targets')


class CampaignPhoneNumber(db.Model):
    __tablename__ = 'campaign_phone_numbers'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign_campaign.id'))
    phone_id = db.Column(db.Integer, db.ForeignKey('campaign_phone.id'), unique=False)


class Target(db.Model):
    __tablename__ = 'campaign_target'

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(STRING_LEN), index=True, nullable=True)  # for US, this is bioguide_id
    title = db.Column(db.String(STRING_LEN), nullable=True)
    name = db.Column(db.String(STRING_LEN), nullable=False, unique=False)
    number = db.Column(phone_number.PhoneNumberType())
    offices = db.relationship('TargetOffice', backref="target")

    def __unicode__(self):
        return self.uid

    def full_name(self):
        return u'{} {}'.format(self.title, self.name)

    def phone_number(self):
        return self.number.e164

    @classmethod
    def get_or_cache_key(cls, uid, prefix=None):
        if prefix:
            key = '%s:%s' % (prefix, uid)
        else:
            key = uid
        t = Target.query.filter(Target.uid == key) \
            .order_by(Target.id.desc()).first()  # return most recently cached target
        cached = False

        if not t:
            adapter = adapt_by_key(key)
            adapted_key, adapter_suffix = adapter.key(key)
            cached_obj = cache.get(adapted_key)
            if type(cached_obj) is list:
                data = adapter.target(cached_obj[0])
                offices = adapter.offices(cached_obj[0])
            elif type(cached_obj) is dict:
                data = adapter.target(cached_obj)
                offices = adapter.offices(cached_obj)
            else:
                # do it live
                data = cached_obj
                offices = cached_obj.get('offices', [])

            # create target object
            t = Target(**data)
            db.session.add(t)
            # create office objects, link to target
            for office in offices:
                if adapter_suffix:
                    if not office['uid'] == adapter_suffix:
                        continue

                o = TargetOffice(**office)
                o.target = t
                db.session.add(o)
            # save to db
            db.session.commit()
            cached = True
        return t, cached


class TargetOffice(db.Model):
    __tablename__ = 'campaign_target_office'

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(STRING_LEN), index=True, nullable=True)  # for US, this is bioguide_id-location_name
    name = db.Column(db.String(STRING_LEN), nullable=True)
    address = db.Column(db.String(STRING_LEN), nullable=True, unique=False)
    location = db.Column(db.String(STRING_LEN), nullable=True, unique=False)
    number = db.Column(phone_number.PhoneNumberType())
    target_id = db.Column(db.Integer, db.ForeignKey('campaign_target.id'))

    def __unicode__(self):
        return u"{} {}".format(self.target, self.type)

    def phone_number(self):
        return self.number.e164

class TwilioPhoneNumber(db.Model):
    __tablename__ = 'campaign_phone'

    id = db.Column(db.Integer, primary_key=True)
    twilio_sid = db.Column(db.String(TWILIO_SID_LENGTH))
    twilio_app = db.Column(db.String(TWILIO_SID_LENGTH))
    call_in_allowed = db.Column(db.Boolean, default=False)
    call_in_campaign_id = db.Column(db.Integer, db.ForeignKey('campaign_campaign.id'))
    number = db.Column(phone_number.PhoneNumberType())

    call_in_campaign = db.relationship('Campaign', foreign_keys=[call_in_campaign_id])

    def __unicode__(self):
        # use e164 for external apis, but international formatting for display
        return self.number.international

    @classmethod
    def available_numbers(*args, **kwargs):
        # returns all existing numbers
        return TwilioPhoneNumber.query
        # should filter_by(call_in_allowed=False), and also include numbers for this campaign

    def set_call_in(self, campaign):
        twilio_client = current_app.config.get('TWILIO_CLIENT')
        twilio_app_name = 'CallPower (%s)' % campaign.name

        # set app VoiceUrl post to campaign url
        campaign_call_url = (url_for('call.incoming', _external=True) +
            '?campaignId=' + str(campaign.id))

        # get or create twilio app by campaign name
        apps = twilio_client.applications.list(friendly_name=twilio_app_name)
        if apps:
            app_sid = apps[0].sid  # there can be only one!
            app = twilio_client.applications.update(app_sid,
                                              friendly_name=twilio_app_name,
                                              voice_url=campaign_call_url,
                                              voice_method="POST")
        else:
            app = twilio_client.applications.create(friendly_name=twilio_app_name,
                                              voice_url=campaign_call_url,
                                              voice_method="POST")

        success = (app.voice_url == campaign_call_url)

        # set twilio number to use app
        twilio_client.phone_numbers.update(self.twilio_sid, voice_application_sid=app.sid)
        self.twilio_app = app.sid
        self.call_in_campaign_id = campaign.id

        return success


class AudioRecording(db.Model):
    __tablename__ = 'campaign_recording'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(STRING_LEN), nullable=False)

    file_storage = db.Column(FlaskStoreType(location='audio/'), nullable=True)
    text_to_speech = db.Column(db.Text)
    version = db.Column(db.Integer)
    description = db.Column(db.String(STRING_LEN))

    hidden = db.Column(db.Boolean, default=False)

    __table_args__ = (UniqueConstraint('key', 'version'),)

    def file_url(self):
        if self.file_storage:
            return self.file_storage.absolute_url
        else:
            return None

    def campaign_names(self):
        recordings = self.campaign_audio_recordings.all()
        names = set([s.campaign.name for s in recordings])
        return ','.join(list(names))

    def campaign_ids(self):
        recordings = self.campaign_audio_recordings.all()
        ids = set([s.campaign.id for s in recordings])
        return list(ids)

    def selected_recordings(self):
        return self.campaign_audio_recordings.filter_by(selected=True).all()

    def selected_campaign_names(self):
        names = set([s.campaign.name for s in self.selected_recordings()])
        return ','.join(list(names))

    def selected_campaign_ids(self):
        ids = set([s.campaign.id for s in self.selected_recordings()])
        return list(ids)

    def __unicode__(self):
        return "%s v%s" % (self.key, self.version)


class CampaignAudioRecording(db.Model):
    __tablename__ = 'campaign_audio_recordings'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign_campaign.id'))
    recording_id = db.Column(db.Integer, db.ForeignKey('campaign_recording.id'))
    selected = db.Column(db.Boolean, default=False)

    campaign = db.relationship('Campaign')
    recording = db.relationship('AudioRecording', backref=db.backref('campaign_audio_recordings',
                                                                     lazy='dynamic'))
