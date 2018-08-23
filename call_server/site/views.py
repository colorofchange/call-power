from flask import Blueprint, render_template, current_app, request
from ..call.views import create, incoming, status_callback
from ..extensions import csrf, cors

site = Blueprint('site', __name__, )
cors(site)
csrf.exempt(site)

@site.route('/')
def index():
    INSTALLED_ORG = current_app.config.get('INSTALLED_ORG', '<YOUR ORG NAME>')
    return render_template('site/index.html', INSTALLED_ORG=INSTALLED_ORG)


# legacy routes to be API-compatible with call-congress
@site.route('/create', methods = ['GET', 'POST'])
def legacy_call_redirect():
	# don't redirect, just return desired function
	return create()

@site.route('/incoming_call', methods = ['GET', 'POST'])
def legacy_call_incoming():
	return incoming()

@site.route('/call_complete_status', methods = ['GET', 'POST'])
def legacy_call_status():
	return status_callback()