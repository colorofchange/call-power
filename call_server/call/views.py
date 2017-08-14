import random
import pystache
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from sqlalchemy_utils.types.phone_number import PhoneNumber, phonenumbers

from flask import abort, Blueprint, request, url_for, current_app
from flask_jsonpify import jsonify
from twilio.base.exceptions import TwilioRestException
from sqlalchemy.sql import desc
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..extensions import csrf, db

from .models import Call, Session
from .constants import TWILIO_TTS_LANGUAGES
from ..campaign.constants import (LOCATION_POSTAL, LOCATION_DISTRICT,
    SEGMENT_BY_LOCATION, SEGMENT_BY_CUSTOM,
    TARGET_OFFICE_DISTRICT, TARGET_OFFICE_BUSY)
from ..campaign.models import Campaign, Target
from ..political_data.lookup import locate_targets
from ..political_data.geocode import LocationError
from ..schedule.models import ScheduleCall
from ..schedule.views import schedule_created, schedule_deleted
from ..admin.models import Blocklist

from .decorators import crossdomain, abortJSON, stripANSI

call = Blueprint('call', __name__, url_prefix='/call')
call_methods = ['GET', 'POST']
csrf.exempt(call)
call.errorhandler(400)(abortJSON)

def play_or_say(r, audio, voice='alice', lang='en-US', **kwargs):
    """
    Take twilio response and play or say message from an AudioRecording
    Can use mustache templates to render keyword arguments
    """

    if audio:
        # check to ensure lang is in list of valid locales
        if lang not in TWILIO_TTS_LANGUAGES:
            if '-' in lang:
                lang, country = lang.split('-')
            else:
                lang = 'en'

        if (hasattr(audio, 'text_to_speech') and audio.text_to_speech):
            msg = pystache.render(audio.text_to_speech, kwargs)
            r.say(msg, voice=voice, language=lang)
        elif (hasattr(audio, 'file_storage') and (audio.file_storage.fp is not None)):
            r.play(audio.file_url())
        elif type(audio) == str:
            try:
                msg = pystache.render(audio, kwargs)
                r.say(msg, voice=voice, language=lang)
            except pystache.common.PystacheError:
                current_app.logger.error('Unable to render pystache template %s' % audio)
                r.say(audio, voice=voice, language=lang)
        else:
            current_app.logger.error('Unknown audio type %s' % type(audio))
    else:
        r.say('Error: no recording defined')
        current_app.logger.error('Missing audio recording')
        current_app.logger.error(kwargs)


def parse_params(r, inbound=False):
    """
    Rehydrate objects from the parameter list.
    Gets invoked before each Twilio call.
    Should not edit param values.
    """
    params = {
        'campaignId': r.values.get('campaignId', None),
        'scheduled': r.values.get('scheduled', None),
        'sessionId': r.values.get('sessionId', None),
        'targetIds': r.values.getlist('targetIds'),
        'userPhone': r.values.get('userPhone', None),
        'userCountry': r.values.get('userCountry', 'us'),
        'userLocation': r.values.get('userLocation', None),
        'userIPAddress': r.values.get('userIPAddress', None)
    }

    if params['userCountry']:
        params['userCountry'] = params['userCountry'].upper()

    if (not params['userPhone']) and not inbound:
        abort(400, 'userPhone required')

    if not params['campaignId']:
        abort(400, 'campaignId required')

    # fallback to zipcode for legacy call-congress compatibility
    if not params['userLocation'] and r.values.get('zipcode', None):
        params['userLocation'] = r.values.get('zipcode')

    # lookup campaign by ID
    if params['campaignId'].isdigit():
        campaign = Campaign.query.get(params['campaignId'])
    else:
        # fallback to name for legacy call-congress compatibility
        campaign = Campaign.query.filter_by(name=params['campaignId']).first()
    if not campaign:
        abort(400, 'invalid campaignId %(campaignId)s' % params)

    if params['userIPAddress'] == None:
        params['userIPAddress'] = r.headers.get('x-forwarded-for', r.remote_addr)

        if "," in params['userIPAddress']:
            ips = params['userIPAddress'].split(", ")
            params['userIPAddress'] = ips[0]

    return params, campaign


def parse_target(key):
    """
    Split target key into (uid, prefix)

    >>> parse_target("us:bioguide_id:ASDF")
    ("ASDF", "us:bioguide_id")
    """
    try:
        pieces = key.split(':')
        uid = pieces[-1]
        prefix = ':'.join(pieces[0:-1])
    except ValueError:
        current_app.logger.error('got malformed target key: "%s"' % key)
        uid = key
        prefix = None
    return (uid, prefix)


def intro_wait_human(params, campaign):
    """
    Play intro message, and wait for key press to ensure we have a human on the line.
    Then, redirect to _make_calls.
    """
    resp = VoiceResponse()

    play_or_say(resp, campaign.audio('msg_intro'))

    action = url_for("call._make_calls", **params)

    # wait for user keypress, in case we connected to voicemail
    # give up after 10 seconds
    g = Gather(num_digits=1, method="POST", timeout=10, action=action)
    play_or_say(g, campaign.audio('msg_intro_confirm'), lang=campaign.language_code)
    resp.append(g)

    return str(resp)


def intro_location_gather(params, campaign):
    """
    If specified, play msg_intro_location audio. Otherwise, standard msg_intro.
    Then, return location_gather.
    """
    resp = VoiceResponse()

    if campaign.audio('msg_intro_location'):
        play_or_say(resp, campaign.audio('msg_intro_location'),
                    organization=current_app.config.get('INSTALLED_ORG', ''),
                    lang=campaign.language_code)
    else:
        play_or_say(resp, campaign.audio('msg_intro'), lang=campaign.language_code)

    return location_gather(resp, params, campaign)


def location_gather(resp, params, campaign):
    """
    Play msg_location, and wait for 5 digits from user.
    Then, redirect to location_parse
    If no response, replay then hang up
    """
    g = Gather(num_digits=5, timeout=5, method="POST", action=url_for("call.location_parse", **params))
    play_or_say(g, campaign.audio('msg_location'), lang=campaign.language_code)
    resp.append(g)
    # didn't get a response
    play_or_say(resp, campaign.audio('msg_unparsed_location'), lang=campaign.language_code)
    resp.append(g) # try second gather
    play_or_say(resp, campaign.audio('msg_goodbye'), lang=campaign.language_code)
    # if no response, hang up

    return str(resp)


def make_calls(params, campaign):
    """
    Connect a user to a sequence of targets.
    Performs target lookup, shuffling, and limiting to maximum.
    Plays msg_call_block_intro, then redirects to make_single call.
    """
    resp = VoiceResponse()

    if not params['targetIds']:
        # check if campaign custom segmenting specified
        if campaign.segment_by == SEGMENT_BY_CUSTOM:
            params['targetIds'] = [t.uid for t in campaign.target_set]
            if campaign.target_ordering == 'shuffle':      
                # reshuffle for each caller
                random.shuffle(params['targetIds'])
        elif campaign.segment_by == SEGMENT_BY_LOCATION:
            # lookup targets for campaign type by segment, put in desired order
            try:
                params['targetIds'] = locate_targets(params['userLocation'], campaign=campaign)
                # locate_targets will include from special target_set if specified in campaign.include_special
            except LocationError, e:
                current_app.logger.error('Unable to locate_targets for %(userLocation)s in %(userCountry)s' % params)
                params['targetIds'] = []
        else:
            current_app.logger.error('Unknown segment_by for campaign %(campaignId)s' % params)
            params['targetIds'] = []
    else:
        # targetIds already set by /create
        pass

    if not params['targetIds']:
        play_or_say(resp, campaign.audio('msg_invalid_location'),
            location=params['userLocation'],
            lang=campaign.language_code)
        resp.hangup()

    # limit calls to maximum number
    if campaign.call_maximum:
        params['targetIds'] = params['targetIds'][:campaign.call_maximum]

    n_targets = len(params['targetIds'])

    play_or_say(resp, campaign.audio('msg_call_block_intro'),
                n_targets=n_targets,
                many=n_targets > 1,
                lang=campaign.language_code)

    resp.redirect(url_for('call.make_single', call_index=0, **params))

    return str(resp)

def schedule_prompt(params, campaign):
    """
    Prompt the user to schedule calls
    """
    if not params or not campaign:
        abort(400)

    resp = VoiceResponse()
    g = Gather(num_digits=1, timeout=3, method="POST", action=url_for("call.schedule_parse", **params))
    
    existing_schedule = ScheduleCall.query.filter_by(campaign_id=campaign.id, phone_number=params['userPhone']).first()
    if existing_schedule and existing_schedule.subscribed:
        play_or_say(g, campaign.audio('msg_alter_schedule'), lang=campaign.language_code)
    else:
        play_or_say(g, campaign.audio('msg_prompt_schedule'), lang=campaign.language_code)
    
    resp.append(g)

    # in case the timeout occurs, we need a redirect verb to ensure that the call doesn't drop
    params['scheduled'] = False
    resp.redirect(url_for('call._make_calls', **params))

    return str(resp)


#####
# EXTERNAL ROUTES
#####

@call.route('/incoming', methods=call_methods)
def incoming():
    """
    Handles incoming calls to the twilio numbers.
    Required Params: campaignId

    Each Twilio phone number needs to be configured to point to:
    server.org/call/incoming?campaignId=12345
    from twilio.com/user/account/phone-numbers/incoming
    """
    params, campaign = parse_params(request, inbound=True)

    if not params or not campaign:
        abort(400)

    if campaign.status == 'archived':
        resp = VoiceResponse()
        play_or_say(resp, campaign.audio('msg_campaign_complete'))
        return str(resp)

    # pull user phone from Twilio incoming request
    params['userPhone'] = request.values.get('From')
    campaign_number = request.values.get('To')

    # create incoming call session
    call_session_data = {
        'campaign_id': campaign.id,
        'from_number': campaign_number,
        'direction': 'inbound'
    }
    if current_app.config['LOG_PHONE_NUMBERS']:
        call_session_data['phone_number'] = params['userPhone']
        # user phone numbers are hashed by the init method
        # but some installations may not want to log at all

    call_session = Session(**call_session_data)
    db.session.add(call_session)
    db.session.commit()

    params['sessionId'] = call_session.id

    if campaign.segment_by == SEGMENT_BY_LOCATION and campaign.locate_by in [LOCATION_POSTAL, LOCATION_DISTRICT]:
        return intro_location_gather(params, campaign)
    else:
        return intro_wait_human(params, campaign)


@call.route('/create', methods=call_methods)
@crossdomain(origin='*')
def create():
    """
    Places a phone call to a user, given a country, phone number, and campaign.

    Required Params:
        userPhone
        campaignId
    Optional Params:
        userCountry (defaults to US)
        userLocation (zipcode)
        targetIds
        record (boolean)
    """
    # parse the info needed to make the call
    params, campaign = parse_params(request)

    # find outgoing phone number in same country as user
    phone_numbers = campaign.phone_numbers(params['userCountry'])

    if not phone_numbers:
        msg = "no numbers available for campaign %(campaignId)s in %(userCountry)s" % params
        return abort(400, msg)

    # validate phonenumber for country
    try:
        parsed = PhoneNumber(params['userPhone'], params['userCountry'])
        userPhone = parsed.e164
    except phonenumbers.NumberParseException:
        current_app.logger.error('Unable to parse %(userPhone)s for %(userCountry)s' % params)
        # press onward, but we may not be able to actually dial
        userPhone = params['userPhone']

    if Blocklist.user_blocked(params['userPhone'], params['userIPAddress'], user_country=params['userCountry']):
        abort(429, {'kthx': 'bai'}) # submission tripped blocklist

    if campaign.status == 'archived':
        result = jsonify(campaign=campaign.status)
        return result

    # start call session for user
    try:
        from_number = random.choice(phone_numbers)

        call_session_data = {
            'campaign_id': campaign.id,
            'location': params['userLocation'],
            'from_number': from_number,
            'direction': 'outbound'
        }
        if current_app.config['LOG_PHONE_NUMBERS']:
            call_session_data['phone_number'] = params['userPhone']
            # user phone numbers are hashed by the init method
            # but some installations may not want to log at all

        call_session = Session(**call_session_data)
        db.session.add(call_session)
        db.session.commit()

        params['sessionId'] = call_session.id

        # initiate outbound call
        call = current_app.config['TWILIO_CLIENT'].calls.create(
            to=userPhone,
            from_=from_number,
            url=url_for('call.connection', _external=True, **params),
            timeout=current_app.config['TWILIO_TIMEOUT'],
            status_callback=url_for("call.status_callback", _external=True, **params),
            status_callback_event=['ringing','completed'],
            record=request.values.get('record', False))

        if campaign.embed:
            script = campaign.embed.get('script')
            redirect = campaign.embed.get('redirect')
        else:
            script = ''
            redirect = ''
        result = jsonify(campaign=campaign.status, call=call.status, script=script, redirect=redirect, fromNumber=from_number)
        result.status_code = 200 if call.status != 'failed' else 500
    except TwilioRestException, err:
        twilio_error = stripANSI(err.msg)
        abort(400, twilio_error)

    return result


@call.route('/connection', methods=call_methods)
@crossdomain(origin='*')
def connection():
    """
    Call handler to connect a user with the targets for a given campaign.
    Redirects to intro_location_gather if campaign requires, or intro_wait_human if not.

    Required Params:
        campaignId
    """
    params, campaign = parse_params(request)

    if not params or not campaign:
        return abortJSON(404)

    if (campaign.segment_by == SEGMENT_BY_LOCATION and
        campaign.locate_by in [LOCATION_POSTAL, LOCATION_DISTRICT] and
        not params['userLocation']):
        return intro_location_gather(params, campaign)
    else:
        return intro_wait_human(params, campaign)


@call.route("/location_parse", methods=call_methods)
def location_parse():
    """
    Handle location entered by the user.
    Required Params: campaignId, Digits
    """
    params, campaign = parse_params(request)

    if not params or not campaign:
        abort(400)

    location = request.values.get('Digits', '')

    # Override locate_by attribute so locate_targets knows we're passing a zip
    # This allows call-ins to be made for campaigns which otherwise use district locate_by
    campaign.locate_by = LOCATION_POSTAL
    # Skip special, because at this point we just want to know if the zipcode is valid
    located_target_ids = locate_targets(location, campaign, skip_special=True)

    if current_app.debug:
        current_app.logger.debug(u'entered = {}'.format(location))

    if not located_target_ids:
        resp = VoiceResponse()
        play_or_say(resp, campaign.audio('msg_invalid_location'),
            lang=campaign.language_code)

        return location_gather(resp, params, campaign)

    params['userLocation'] = location
    call_session = Session.query.get(params['sessionId'])
    if not call_session.location:
        call_session.location = location
        db.session.add(call_session)
        db.session.commit()

    resp = VoiceResponse()
    resp.redirect(url_for('call._make_calls', **params))
    return str(resp)


@call.route("/schedule_parse", methods=call_methods)
def schedule_parse():
    """
    Handle schedule response entered by user
    Required Params: campaignId, Digits
    """
    params, campaign = parse_params(request)
    resp = VoiceResponse()

    if not params or not campaign:
        abort(400)

    schedule_choice = request.values.get('Digits', '')

    if current_app.debug:
        current_app.logger.debug(u'entered = {}'.format(schedule_choice))

    if schedule_choice == "1":
        # schedule a call at this time every day
        play_or_say(resp, campaign.audio('msg_schedule_start'),
            lang=campaign.language_code)
        scheduled = True
        schedule_created.send(ScheduleCall,
            campaign_id=campaign.id,
            phone=params['userPhone'],
            location=params['userLocation'])
    elif schedule_choice == "9":
        # user wishes to opt out
        play_or_say(resp, campaign.audio('msg_schedule_stop'),
            lang=campaign.language_code)
        scheduled = False
        schedule_deleted.send(ScheduleCall,
            campaign_id=campaign.id,
            phone=params['userPhone'])
    else:
        # because of the timeout, we may not have a digit
        scheduled = False

    params['scheduled'] = scheduled
    resp.redirect(url_for('call._make_calls', **params))
    return str(resp)


@call.route('/make_calls', methods=call_methods)
def _make_calls():
    """
    Start to make calls, scheduling daily calls if desired.
    """
    params, campaign = parse_params(request)

    if not params or not campaign:
        abort(400)

    if campaign.prompt_schedule and not params.get('scheduled'):
        return schedule_prompt(params, campaign)
    else:
        return make_calls(params, campaign)


@call.route('/make_single', methods=call_methods)
def make_single():
    params, campaign = parse_params(request)

    if not params or not campaign:
        abort(400)

    i = int(request.values.get('call_index', 0))
    params['call_index'] = i

    (uid, prefix) = parse_target(params['targetIds'][i])
    (current_target, cached) = Target.get_or_cache_key(uid, prefix)
    if cached:
        # save Target to database
        db.session.add(current_target)
        db.session.commit()

    resp = VoiceResponse()

    if not current_target.number:
        play_or_say(resp, campaign.audio('msg_invalid_location'),
            lang=campaign.language_code)
        return str(resp)

    if current_target.offices:
        if campaign.target_offices == TARGET_OFFICE_DISTRICT:
            office = random.choice(current_target.offices)
            target_phone = office.number
        elif campaign.target_offices == TARGET_OFFICE_BUSY:
            # TODO keep track of which ones we have tried
            undialed_offices = current_target.offices
            # then pick a random one
            office = random.choice(undialed_offices)
            target_phone = office.number
        #elif campaign.target_offices == TARGET_OFFICE_CLOSEST:
        #   office = find_closest(current_target.offices, params['userLocation'])
        #   target_phone = office.phone
        else:
            office = None
            target_phone = current_target.number
    else:
        office = None
        target_phone = current_target.number
        
    play_or_say(resp, campaign.audio('msg_target_intro'),
        title=current_target.title,
        name=current_target.name,
        office_type = office.name if office else '',
        lang=campaign.language_code)

    if current_app.debug:
        current_app.logger.debug(u'Call #{}, {} ({}) from {} in call.make_single()'.format(
            i, current_target.name, target_phone.e164, params['userPhone']))

    try:
        parsed = PhoneNumber(params['userPhone'], params['userCountry'])
        userPhone = parsed.e164
    except phonenumbers.NumberParseException:
        current_app.logger.error('Unable to parse %(userPhone)s for %(userCountry)s' % params)
        # press onward, but we may not be able to actually dial
        userPhone = params['userPhone']

    # sending a twiml.Number to dial init will not nest properly
    # have to add it after creation
    d = Dial(None, caller_id=userPhone,
              time_limit=current_app.config['TWILIO_TIME_LIMIT'],
              timeout=current_app.config['TWILIO_TIMEOUT'], hangup_on_star=True,
              action=url_for('call.complete', **params)) \
        .number(target_phone.e164, sendDigits=target_phone.extension)
    resp.append(d)

    return str(resp)


@call.route('/complete', methods=call_methods)
def complete():
    params, campaign = parse_params(request)
    i = int(request.values.get('call_index', 0))

    if not params or not campaign:
        abort(400)

    (uid, prefix) = parse_target(params['targetIds'][i])
    (current_target, cached) = Target.get_or_cache_key(uid, prefix)
    call_data = {
        'session_id': params['sessionId'],
        'campaign_id': campaign.id,
        'target_id': current_target.id,
        'call_id': request.values.get('CallSid', None),
        'status': request.values.get('DialCallStatus', 'unknown'),
        'duration': request.values.get('DialCallDuration', 0)
    }

    try:
        db.session.add(Call(**call_data))
        db.session.commit()
    except SQLAlchemyError:
        current_app.logger.error('Failed to log call:', exc_info=True)

    resp = VoiceResponse()

    if call_data['status'] == 'busy':
        play_or_say(resp, campaign.audio('msg_target_busy'),
            title=current_target.title,
            name=current_target.name,
            lang=campaign.language_code)

    # TODO if district offices, try another office number

    i = int(request.values.get('call_index', 0))

    if i == len(params['targetIds']) - 1:
        # thank you for calling message
        play_or_say(resp, campaign.audio('msg_final_thanks'),
            lang=campaign.language_code)
    else:
        # call the next target
        params['call_index'] = i + 1  # increment the call counter
        calls_left = len(params['targetIds']) - i - 1

        play_or_say(resp, campaign.audio('msg_between_calls'),
            calls_left=calls_left,
            lang=campaign.language_code)

        resp.redirect(url_for('call.make_single', **params))

    return str(resp)


@call.route('/status_callback', methods=call_methods)
def status_callback():
    # async callback from twilio on call events
    params, _ = parse_params(request)

    if not params:
        abort(400)

    if not params.get('sessionId'):
        return jsonify({
            'phoneNumber': request.values.get('From', ''),
            'callStatus': 'unknown',
            'message': 'no sessionId passed, unable to update status',
            'campaignId': params['campaignId']
        })

    if request.values.get('CallStatus') == 'ringing':
        # update call_session with time interval calculated in Twilio queue
        call_session = Session.query.get(request.values.get('sessionId'))
        call_session.queue_delay = datetime.utcnow() - call_session.timestamp
        db.session.add(call_session)
        db.session.commit()

    # CallDuration only present when call is complete
    # update call_session with status, duration
    if request.values.get('CallDuration'):
        call_session = Session.query.get(request.values.get('sessionId'))
        call_session.status = request.values.get('CallStatus', 'unknown')
        call_session.duration = request.values.get('CallDuration', None)
        db.session.add(call_session)
        db.session.commit()

    return jsonify({
        'phoneNumber': request.values.get('To', ''),
        'callStatus': request.values.get('CallStatus'),
        'targetIds': params['targetIds'],
        'campaignId': params['campaignId']
    })


@call.route('/status_inbound', methods=call_methods)
def status_inbound():
    # async callback from twilio on inbound call complete
    params, campaign = parse_params(request, inbound=True)

    if not params:
        abort(400)

    # find call_session from number with direction inbound that is not complete
    # if there's more than one, get the most recent one
    user_phone = request.values.get('From', '')
    phone_hash = Session.hash_phone(user_phone)
    call_session = Session.query.filter_by(
        phone_hash=phone_hash,
        status='initiated',
        direction='inbound',
        campaign_id=campaign.id,
        location=params['userLocation']
    ).order_by(desc(Session.timestamp)).first()
    if call_session:
        call_session.status = request.values.get('CallStatus', 'unknown')
        call_session.duration = request.values.get('CallDuration', None)
        db.session.add(call_session)
        db.session.commit()

        return jsonify({
            'phoneNumber': request.values.get('From', ''),
            'callStatus': call_session.status,
            'campaignId': params['campaignId']
        })
    else:
        return jsonify({
            'phoneNumber': request.values.get('From', ''),
            'callStatus': 'unknown',
            'message': 'unable to find CallSession matching campaign, location, and phone',
            'campaignId': params['campaignId']
        })
