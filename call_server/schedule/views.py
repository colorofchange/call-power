from flask import (Blueprint, current_app, request, url_for, jsonify)
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

####
# CRUD
# these work both as web-routes and signal-ized functions
####

@schedule.route("/<int:campaign_id>/<phone>", methods=['POST'])
def create(campaign_id, phone, location=None):
    campaign = Campaign.query.filter_by(id=campaign_id).first_or_404()
    if _create(ScheduleCall, campaign.id, phone, location, time=request.args.get('time')):
        return jsonify('ok')

def _create(cls, campaign_id, phone, location=None, time=None):
    schedule_call, created = get_one_or_create(db.session, ScheduleCall,
                            campaign_id=campaign_id, phone_number=phone)
    if time:
        schedule_call.time_to_call = time
    else:
        # reset to now
        schedule_call.time_to_call = utc_now().time()
    current_app.logger.info('%s at %s' % (schedule_call, schedule_call.time_to_call))
    schedule_call.start_job(location=location)
    db.session.add(schedule_call)
    db.session.commit()
    return True
schedule_created.connect(_create, ScheduleCall)

@schedule.route("/<int:campaign_id>/<phone>", methods=['DELETE'])
def delete(campaign_id, phone):
    campaign = Campaign.query.filter_by(id=campaign_id).first_or_404()
    if _delete(ScheduleCall, campaign.id, phone):
        return jsonify('gone')

def _delete(cls, campaign_id, phone):
    schedule_call = ScheduleCall.query.filter_by(campaign_id=campaign_id, phone_number=phone).first_or_404()
    schedule_call.stop_job()
    # don't actually delete the object, keep it for stats
    db.session.add(schedule_call)
    db.session.commit()
    return True
schedule_deleted.connect(_delete, ScheduleCall)


