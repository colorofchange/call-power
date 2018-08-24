from flask import (Blueprint, request, jsonify)
from flask_login import login_required

from ..extensions import cache
from ..utils import ignore_accents
from . import get_country_data

import logging

log = logging.getLogger(__name__)
political_data = Blueprint('political_data', __name__, url_prefix='/political_data')

# all political_data routes require login
@political_data.before_request
@login_required
def before_request():
    pass

@political_data.route('/search')
def search():
    # really basic search based on political_data cache keys
    country = request.args.get('country', 'us')
    data_provider = get_country_data(country, cache=cache)
    if not data_provider:
        return jsonify({'status': 'error',
                        'message': 'unable to search '+country})

    keys = request.args.getlist('key')
    if not keys:
        return jsonify({'status': 'error',
                        'message': 'no key provided'})

    results = []
    for k in keys:
        results.extend(data_provider.cache_search(k))

    filters = request.args.getlist('filter')
    for f in filters:
        try:
            field, value = f.split('=')
            value = ignore_accents(value.lower()) # ensure comparison ignores accented characters
            results = [d for d in results if ignore_accents(d[field]).lower().startswith(value)]
        except ValueError,e:
          log.error(e)
          continue

    return jsonify({
        'status': 'ok',
        'results': results
    })
