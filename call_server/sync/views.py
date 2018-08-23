from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from flask_login import login_required
from datetime import datetime, timedelta

from .jobs import sync_campaigns

sync = Blueprint('sync', __name__, url_prefix='/admin/crmsync')


# all sync routes require login
@sync.before_request
@login_required
def before_request():
    pass


@sync.route('/<int:campaign_id>/', methods=['POST'])
def manual_job(campaign_id):
    # start sync job out of band with rq scheduler
    start_time = datetime.now() + timedelta(seconds=1)
    sync_campaigns.schedule(start_time, campaign_id)

    return jsonify({'scheduled_start_time': start_time})