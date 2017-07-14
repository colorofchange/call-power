from flask import current_app
from flask_babel import gettext as _
import werkzeug.contrib.cache
import pickle

class DataProvider(object):
    country_name = None
    campaign_types = []

    SORTED_SETS = []

    def __init__(self, **kwargs):
        pass

    def load_data(self):
        """
        Loads all country-specific data and caches the result
        """
        raise NotImplementedError()

    def get_location(self, locate_by, raw):
        """
        @return  a location within the country using the given raw input
        """
        raise NotImplementedError()

    @property
    def campaign_type_choices(self):
        return [(key, campaign_type.type_name) for key, campaign_type in self.campaign_types]

    def get_campaign_type(self, type_id):
        type_class = dict(self.campaign_types).get(type_id)
        return type_class(self)

    def cache_get(self, key, default=list()):
        """
        Checks for key in cache and returns it, or default
        This is needed because werkzeug caches don't return defaults like dicts do
        """
        return self._cache.get(key) or default

    def cache_set(self, key, value):
        """ Add a new key/value to the cache """
        if hasattr(self._cache, 'set'):
            self._cache.set(key, value)
        elif hasattr(self._cache, 'update'):
            self._cache.update({key:value})
        else:
            raise AttributeError('cache does not appear to be dict-like')

    def cache_set_many(self, mapping):
        """
        Sets multiple keys and values from a mapping.
        Handles difference between flask-cache and mock-dictionary
        """
        if hasattr(self._cache, 'set_many'):
            self._cache.set_many(mapping)
        elif hasattr(self._cache, 'update'):
            self._cache.update(mapping)
        else:
            raise AttributeError('cache does not appear to be dict-like')

    def cache_search(self, key_starts_with):
        """
        Searches for keys starting with a name
        Handles difference between flask-cache and mock-dictionary
        """
        result = []
        if isinstance(self._cache.cache, werkzeug.contrib.cache.RedisCache):
            redis = self._cache.cache._client

            # check sorted sets first
            for s in self.SORTED_SETS:
                if key_starts_with.startswith(s):
                    # weird redis syntax for min/max
                    min_val = u'[' + key_starts_with
                    max_val = u'(' + key_starts_with + u'\xff'
                    matching_keys = redis.zrangebylex(s, min_val, max_val)
                    for key in matching_keys:
                        result.extend(self.cache_get(key))

            # fall back on key scan
            # can be fairly slow (3-4s for full scan)
            if not result:
                key_scan = current_app.config['CACHE_KEY_PREFIX'] + key_starts_with + '*'
                for prefixed_key in redis.scan_iter(match=key_scan):
                    key = prefixed_key.replace(current_app.config['CACHE_KEY_PREFIX'], '')
                    result.extend(self.cache_get(key))
        elif isinstance(self._cache.cache, werkzeug.contrib.cache.SimpleCache):
            # naively search across all the keys
            for (k,v) in self._cache.cache._cache.items():
                if k.startswith(key_starts_with):
                    wet_value = pickle.loads(v[1])
                    if isinstance(wet_value, list):
                        result.extend(wet_value)
                    else:
                        result.append(wet_value)
        else:
            raise AttributeError('cannot search cache. it should be a redis connection or a dict')
        return result

class CampaignType(object):
    type_name = None
    subtypes = []
    target_orders = [
        ('in-order', _("In order")),
        ('shuffle', _("Shuffle")),
    ]

    def __init__(self, data_provider):
        self.data_provider = data_provider

    @property
    def region_choices(self):
        """
        @return  a list of political regions for this campaign type
        """
        return []

    def all_targets(self, location, campaign_region=None):
        """
        Find all targets for a location, crossing political boundaries if
        necessary.
        @return  a dictionary of target uids grouped by subtype.
        """
        raise NotImplementedError()

    def sort_targets(self, targets, subtype, order):
        """
        Sort and filter a dictionary of targets (grouped by subtype), as
        returned from all_targets, based on the provided subtype and order.
        @return  a list of sorted and filtered target uids
        """
        raise NotImplementedError()

    @property
    def country_name(self):
        return self.data_provider.country_name

    @property
    def country_code(self):
        return self.data_provider.country_code

    @property
    def subtype_choices(self):
        return CampaignType.subtypes + self.subtypes

    def get_subtype_display(self, subtype, campaign_region=None):
        choices_dict = dict(self.subtype_choices)
        return choices_dict.get(subtype, None)

    @property
    def target_order_choices(self):
        return CampaignType.target_orders + self.target_orders

    def get_order_display(self, target_order):
        choices_dict = dict(self.target_order_choices)
        return choices_dict.get(target_order, None)

    def get_targets_for_campaign(self, location, campaign):
        country_code = campaign.country_code
        if isinstance(location, basestring):
            location = self.data_provider.get_location(campaign.locate_by, location)
        all_targets = self.all_targets(location, campaign.campaign_state)
        return self.sort_targets(all_targets, campaign.campaign_subtype, campaign.target_ordering)
