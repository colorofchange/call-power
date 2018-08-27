from . import DataProvider, CampaignType

from ..geocode import Geocoder, LocationError
from ...campaign.constants import (LOCATION_POSTAL, LOCATION_ADDRESS, LOCATION_LATLON)

import logging
log = logging.getLogger(__name__)

class EUCampaignType(CampaignType):
    pass

class EUCampaignType_Custom(EUCampaignType):
    type_name = "Custom - MEP"

class EUDataProvider(DataProvider):
    # data provider for Members of European Parliament
    campaign_types = [
        ('custom', EUCampaignType_Custom)
    ]

    def __init__(self, cache, **kwargs):
        super(EUDataProvider, self).__init__(**kwargs)
        self._cache = cache
        self._geocoder = Geocoder(country=self.country_code.upper())

    def load_data(self):
        # no stored data to load for this data provider
        return 0

class FRDataProvider(EUDataProvider):
    country_name = "France"
    country_code = "fr"

class DEDataProvider(EUDataProvider):
    country_name = "Germany"
    country_code = "de"

class ESDataProvider(EUDataProvider):
    country_name = "Spain"
    country_code = "es"

class IRDataProvider(EUDataProvider):
    country_name = "Ireland"
    country_code = "ir"

class ITDataProvider(EUDataProvider):
    country_name = "Italy"
    country_code = "it"

class PLDataProvider(EUDataProvider):
    country_name = "Poland"
    country_code = "pl"

class UKDataProvider(EUDataProvider):
    country_name = "United Kingdom"
    country_code = "uk"
