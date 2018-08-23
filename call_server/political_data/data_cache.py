from flask import current_app
from ..extensions import cache
from ..political_data.adapters import adapt_by_key
import pyopenstates

def check_political_data_cache(key, cache=cache):
    adapter = adapt_by_key(key)
    adapted_key, adapter_suffix = adapter.key(key)
    cached_obj = cache.get(adapted_key)

    if not cached_obj:
        # some keys may not be in our local cache
        # but may be available over external APIs
        if adapted_key.startswith("us_state:openstates"):
            leg_id = key.split(':')[-1]
            leg = pyopenstates.get_legislator(leg_id)
            leg['cache_key'] = key
            cache.set(key, leg)
            cached_obj = leg

    if type(cached_obj) is list:
        data = adapter.target(cached_obj[0])
        offices = adapter.offices(cached_obj[0])
    elif type(cached_obj) is dict:
        data = adapter.target(cached_obj)
        offices = adapter.offices(cached_obj)
    else:
        current_app.logger.error('Target.check_political_data_cache got unknown cached_obj type %s for key %s' % (type(cached_obj), key))
        # do it live
        if cached_obj:
            data = cached_obj
        else:
            data = {}
        try:
            offices = cached_obj.get('offices', [])
        except AttributeError:
            offices = []

    data['uid'] = adapted_key
    data['offices'] = offices
    return data
