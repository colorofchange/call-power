from datetime import datetime
from flask import (Blueprint, current_app, request, url_for, jsonify, make_response)
from flask_login import login_required
from blinker import Namespace

from .models import ScheduleCall
from ..campaign.models import Campaign

from ..extensions import csrf, db
from ..utils import get_one_or_create, utc_now

schedule = Blueprint('schedule', __name__, url_prefix='/schedule')
csrf.exempt(schedule)

namespace = Namespace()
schedule_created = namespace.signal('schedule_created')
schedule_deleted = namespace.signal('schedule_deleted')

@schedule.before_request
@login_required
def before_request():
    # all schedule routes require login
    pass

####
# CRUD
# these work both as web-routes and signal-ized functions
####

@schedule.route("/<int:campaign_id>/<phone>", methods=['POST'])
def create(campaign_id, phone, location=None):
    campaign = Campaign.query.filter_by(id=campaign_id).first_or_404()
    
    set_time = None
    if request.form.get('time'):
        # time is specified as UTC, enforce it
        try:
            parsed_time = datetime.strptime(request.form.get('time')+' UTC', '%H:%M %Z')
            set_time = parsed_time.time()
        except ValueError:
             return make_response(jsonify({'error': 'time format must be %H:%M:%S'}), 400) 

    if _create(ScheduleCall, campaign.id, phone, location, time=set_time):
        return make_response(jsonify({'status': 'ok'}), 200)

def _create(cls, campaign_id, phone, location=None, time=None):
    schedule_call, created = get_one_or_create(db.session, ScheduleCall,
                            campaign_id=campaign_id, phone_number=phone)
    if time:
        schedule_call.time_to_call = time
    else:
        # reset to now
        schedule_call.time_to_call = utc_now().time()

    if schedule_call.job_id:
        # existing schedule, stop it before re-scheduling
        schedule_call.stop_job()

    current_app.logger.info('%s at %s UTC' % (schedule_call, schedule_call.time_to_call))
    schedule_call.start_job(location=location)
    db.session.add(schedule_call)
    db.session.commit()
    return True
schedule_created.connect(_create, ScheduleCall)

@schedule.route("/<int:campaign_id>/<phone>", methods=['DELETE'])
def delete(campaign_id, phone):
    campaign = Campaign.query.filter_by(id=campaign_id).first_or_404()
    if _delete(ScheduleCall, campaign.id, phone):
        return make_response(jsonify({'status': 'deleted'}), 200)
    else:
        return make_response(jsonify({'status': 'nope'}), 404)

def _delete(cls, campaign_id, phone):
    schedule_call = ScheduleCall.query.filter_by(campaign_id=campaign_id, phone_number=phone).first()
    if not schedule_call:
        return False
    schedule_call.stop_job()
    # don't actually delete the object, keep it for stats
    db.session.add(schedule_call)
    db.session.commit()
    return True
schedule_deleted.connect(_delete, ScheduleCall)


