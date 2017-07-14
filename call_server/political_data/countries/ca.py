from flask_babel import gettext as _

import represent
from . import DataProvider, CampaignType

from ..geocode import Geocoder, LocationError
from ..constants import CA_PROVINCE_ABBR_DICT
from ...campaign.constants import (LOCATION_POSTAL, LOCATION_ADDRESS, LOCATION_LATLON)

import logging
log = logging.getLogger(__name__)

class CACampaignType(CampaignType):
    pass


class CACampaignType_Local(CACampaignType):
    type_name = "Local"


class CACampaignType_Custom(CACampaignType):
    type_name = "Custom"


class CACampaignType_Executive(CACampaignType):
    type_name = "Executive"

    subtypes = [
        ('exec', _("Prime Minister")),
        ('office', _("Office"))
    ]

    def all_targets(self, location, campaign_region=None):
        return {
            'exec': self._get_executive()
        }

    def _get_executive(self):
        return self.data_provider.get_executive()


class CACampaignType_Parliament(CACampaignType):
    type_name = "Parliament"

    subtypes = [
        ('lower', _("House of Commons"))
    ]
    target_orders = [
        ('lower-first', _("House of Commons"))
    ]

    def all_targets(self, location, campaign_region=None):
        return {
            'lower': self._get_member_of_parliament(location)
        }

    def sort_targets(self, targets, subtype, order):
        result = []

        if subtype == 'lower':
            result.extend(targets.get('lower'))

        return result

    def _get_member_of_parliament(self, location):
        reps = self.data_provider.get_representatives(location)
        filtered = self._filter_representatives(reps, "MP")
        return (r['cache_key'] for r in filtered)

    def _filter_representatives(self, representatives, elected_office="MP", campaign_region=None):
        for key in representatives:
            rep = self.data_provider.cache_get(key, {})
            correct_office = rep['elected_office'].upper() == elected_office
            in_region = campaign_region is None or rep['district_name'].upper() == campaign_region.upper()
            if correct_office and in_region:
                yield rep


class CACampaignType_Province(CACampaignType):
    type_name = "Province"

    subtypes = [
        ('lower', _("Legislature"))
    ]
    target_orders = [
        ('lower-first', _("Legislature"))
    ]

    # as available at http://represent.opennorth.ca/data/
    provincial_legislatures = {
        'AB': {'body': 'alberta-legislature', 'office': 'MLA'},
        'BC': {'body': 'bc-legislature', 'office': 'MLA'},
        'MB': {'body': 'manitoba-legislature', 'office': 'MLA'},
        'NB': {'body': 'new-brunswick-legislature', 'office': 'MLA'},
        'NL': {'body': 'newfoundland-labrador-legislature', 'office': 'MHA'},
        #'NT': 'Northwest Territories',
        'NS': {'body': 'nova-scotia-legislature', 'office': 'MLA'},
        #'NU': 'Nunavut',
        'ON': {'body': 'ontario-legislature', 'office': 'MPP'},
        'PE': {'body': 'pei-legislature', 'office': 'MLA'},
        'QC': {'body': 'quebec-assemblee-nationale', 'office': 'MNA'},
        'SK': {'body': 'saskatchewan-legislature', 'office': 'MLA'},
        #'YT': 'Yukon',
   }
   

    @property
    def region_choices(self):
        province_choices = {'': ''}
        for abbr in self.provincial_legislatures:
            province_choices[abbr] = CA_PROVINCE_ABBR_DICT.get(abbr)
        return province_choices

    def get_subtype_display(self, subtype, campaign_region=None):
        display = super(CACampaignType_Province, self).get_subtype_display(subtype, campaign_region)
        if display:
            return u'{} - {}'.format(campaign_region, display)
        else:
            return display

    def all_targets(self, location, campaign_region=None):
        return {
            'lower': self._get_province_representative(location, campaign_region),
        }

    def sort_targets(self, targets, subtype, order):
        result = []

        if subtype == 'lower':
            result.extend(targets.get('lower'))

        return result

    def _get_province_representative(self, location, campaign_region=None):
        legislature = self.provincial_legislatures.get(campaign_region)
        reps = self.data_provider.get_representatives(location, legislature['body'])
        filtered = self._filter_representatives(reps, legislature['office'])
        return (r['cache_key'] for r in filtered)

    def _filter_representatives(self, representatives, elected_office="MLA", district_name=None):
        for key in representatives:
            rep = self.data_provider.cache_get(key, {})
            correct_office = rep['elected_office'].upper() == elected_office
            in_region = district_name is None or rep['district_name'].upper() == district_name.upper()
            if correct_office and in_region:
                yield rep

class CADataProvider(DataProvider):
    country_name = "Canada"
    country_code = "ca"

    campaign_types = [
        ('executive', CACampaignType_Executive),
        ('parliament', CACampaignType_Parliament),
        ('province', CACampaignType_Province),
        ('local', CACampaignType_Local),
        ('custom', CACampaignType_Custom)
    ]

    KEY_OPENNORTH = 'ca:opennorth:{boundary}'

    def __init__(self, cache, **kwargs):
        super(CADataProvider, self).__init__(**kwargs)
        self._cache = cache
        self._geocoder = Geocoder(country='CA')

    def get_location(self, locate_by, raw):
        if locate_by == LOCATION_POSTAL:
            return self._geocoder.postal(raw)
        elif locate_by == LOCATION_ADDRESS:
            return self._geocoder.geocode(raw)
        elif locate_by == LOCATION_LATLON:
            return self._geocoder.reverse(raw)
        else:
            return None


    def load_data(self):
        # we don't have an easy mapping of postcode to riding
        # so just hit OpenNorth with every request and cache responses
        log.info('no data to load for political_data.countries.ca')
        self.cache_set('political_data:ca', ['data sourced from represent.opennorth.ca',])
        return 0
        

    # convenience methods for easy district access
    def get_executive(self):
        # return Prime Minister's comment line
        return [{'office': 'Prime Minister\'s Office',
                'number': '16139924211'}]


    def get_postcode(self, postcode):
        return represent.postcode(code=postcode)


    def get_representatives(self, location, body_name='house-of-commons'):
        if not location or not (location.latitude and location.longitude):
            raise LocationError('CADataProvider.get_representatives requires location with lat/lon')

        point = "{},{}".format(location.latitude, location.longitude)
        reps = represent.representative(point=point, repr_set=body_name)
        # add throttle=False here to avoid rate limits

        # calculate keys and cache responses
        keys = []
        for rep in reps:
            boundary_key = self.boundary_url_to_key(rep['related']['boundary_url'])
            cache_key = self.KEY_OPENNORTH.format(boundary=boundary_key)
            rep['boundary_key'] = boundary_key
            rep['cache_key'] = cache_key
            self.cache_set(cache_key, rep)
            keys.append(cache_key)

        return keys


    def get_uid(self, uid):
        return [self.cache_get(uid, dict())]


    def get_boundary_key(self, boundary_key):
        key = self.KEY_OPENNORTH.format(boundary=boundary_key)
        return self.cache_get(key, dict())


    def boundary_url_to_key(self, related_url):
        # convert OpenNorth's related boundary url to cache key
        boundary = related_url.strip('/')
        boundary = boundary.replace('boundaries/', '')
        key = boundary.replace('/', ':')
        return key

