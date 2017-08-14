import geopy
import os

from constants import US_STATE_NAME_DICT, CA_PROVINCE_NAME_DICT

GOOGLE_SERVICE = 'GoogleV3'
SMARTYSTREETS_SERVICE = 'LiveAddress'
SMARTYSTEETS_ZIPCODE_SERVICE = 'SmartyStreetsUSZipcode'
NOMINATIM_SERVICE = 'Nominatim'
LOCAL_USDATA_SERVICE = 'LocalUSDataProvider'

class Location(geopy.Location):
    """
    a light wrapper around the geopy location object
    which can return properties from the raw address components 
    """

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], geopy.Location):
            self._wrapped_obj = args[0]
        else:
            super(Location, self).__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        elif self._wrapped_obj and attr in dir(self._wrapped_obj):
            return getattr(self._wrapped_obj, attr)
        else:
            raise AttributeError('Location object has no attribute %s' % attr)

    def __repr__(self):
        try:
            if self.latitude and self.longitude: 
                return "Location((%s, %s, %s))" % (
                    self.latitude, self.longitude, self.altitude
                )
        except AttributeError:
            pass
        try:
            return "Location(%s) - %s" % ( self.postal, self.service )
        except AttributeError:
            pass
        try:
            return "Location(%s) - %s" % ( self.address, self.service )
        except AttributeError:
            pass
        try:
            return "Location(%s) - %s" % ( self.raw, self.service )
        except AttributeError:
            pass

        return "Location(%s)" % self.__dict__


    def _find_in_raw(self, field):
        """
        finds a component by type name in raw address_components
        """
        if not self.raw:
            return None

        try:
            if self.service == GOOGLE_SERVICE:
                # google style, raw.address_components are a list of dicts, with types in list
                for c in self.raw['address_components']:
                    if field in c['types']:
                        return c['short_name']
                return None
            elif self.service == SMARTYSTREETS_SERVICE:
                # smarty streets style, raw.components are named
                return self.raw['components'].get(field)
            elif self.service == SMARTYSTEETS_ZIPCODE_SERVICE:
                return self.raw.get(field)
            elif self.service == NOMINATIM_SERVICE:
                return self.raw['address'].get(field)
            elif self.service == LOCAL_USDATA_SERVICE:
                return self.raw.get(field)
            else:
                # try simple extraction from raw
                return self.raw.get(field)
        except KeyError:
            try:
                # fallback to raw
                return self.raw.get(field)
            except KeyError, ValueError:
                raise ValueError('unable to parse raw fields from geocoder service '+self.service)

    @property
    def service(self):
        if hasattr(self, '_service'):
            return self._service
        else:
            return "UnknownService"

    @service.setter
    def service(self, value):
        self._service = value

    @property
    def state(self):
        if self.service == GOOGLE_SERVICE:
            return self._find_in_raw('administrative_area_level_1')
        elif self.service in [SMARTYSTREETS_SERVICE,SMARTYSTEETS_ZIPCODE_SERVICE]:
            return self._find_in_raw('state_abbreviation')
        elif self.service == NOMINATIM_SERVICE:
            if self._find_in_raw('country_code') == 'us':
                state_name = self._find_in_raw('state')
                return US_STATE_NAME_DICT.get(state_name)
            elif self._find_in_raw('country_code') == 'ca':
                province_name = self._find_in_raw('state')
                return CA_PROVINCE_NAME_DICT.get(province_name)
        else:
            return self._find_in_raw('state')

    @property
    def latlon(self):
        lat = self.latitude
        lon = self.longitude
        return (lat, lon)

    @property
    def postal(self):
        if self.service == GOOGLE_SERVICE:
            return self._find_in_raw('postal_code')
        elif self.service == SMARTYSTREETS_SERVICE:
            return self._find_in_raw('zipcode')
        elif self.service == NOMINATIM_SERVICE:
            return self._find_in_raw('postcode')
        elif self.service == LOCAL_USDATA_SERVICE:
            return self._find_in_raw('zipcode')
        else:
            return self._find_in_raw('zipcode')


class LocationError(TypeError):
    pass

class Geocoder(object):
    """
    a light wrapper around the geopy client
    with configurable service name
    """

    def __init__(self, API_NAME=None, API_KEY=None, country='US'):
        if not (API_NAME or API_KEY):
            # get keys from os.environ, because we may not have current_app context
            API_NAME = os.environ.get('GEOCODE_PROVIDER', 'nominatim').lower()  # default to the FOSS provider
            API_KEY = os.environ.get('GEOCODE_API_KEY', None)

        service = geopy.geocoders.get_geocoder_for_service(API_NAME)
        self.country = country

        if API_NAME == 'nominatim':
                # nominatim sets country bias at init
                # and has no API_KEY
                self.client = service(country_bias=country, timeout=5)
        elif API_NAME == 'liveaddress':
            AUTH_TOKEN = os.environ.get('GEOCODE_API_TOKEN', None)
            self.client = service(API_KEY, AUTH_TOKEN, timeout=3)
            # SmartyStreets has a separate US Zipcode endpoint
            self.client_uszipcode = SmartystreetsUSZipcode(API_KEY, AUTH_TOKEN)
        elif API_KEY:
            self.client = service(api_key=API_KEY, timeout=3)
        else:
            raise LocationError('configure your geocoder with environment variables GEOCODE_PROVIDER and GEOCODE_API_KEY')
            

    def get_service_name(self):
        "returns geopy.geocoder class name, like GoogleV3, LiveAddress, Nominatim, etc"
        return self.client.__class__.__name__.split('.')[-1]

    def postal(self, code, country='us', provider=None):
        if provider and country == 'us':
            districts = provider.get_districts(code)
            if districts:
                d = districts[0]
                l = Location(code, (None, None), d)
                l.service = 'LocalUSDataProvider'
                return l

        # fallback to geocoder if cache unavailable
        return self.geocode(code, postal_only=True)

    def geocode(self, address, postal_only=False):
        service = self.get_service_name()

        try:
            if service == GOOGLE_SERVICE:
                response = self.client.geocode(address, region=self.country)
                # bias responses to region/country (2-letter TLD)           
            elif service == NOMINATIM_SERVICE:
                # nominatim won't return metadata unless we ask
                response = self.client.geocode(address, addressdetails=True)
                if not response:
                    return Location()
                intermediate = Location(response)
                if postal_only or (not intermediate.postal):
                    # nominatim doesn't give full location for lots of queries
                    # so take the response, flip it and reverse it
                    reverse_response = self.client.reverse(intermediate.latlon)
                    response = reverse_response
            elif service == SMARTYSTREETS_SERVICE:
                if postal_only:
                    # smarty has a separate US Zipcode API endpoint
                    response = self.client_uszipcode.geocode(address)
                else:
                    # hit main liveaddress, just want return one response
                    response = self.client.geocode(address, exactly_one=True)
            else:
                response = self.client.geocode(address)

            result = Location(response)
            result.service = service

            # override service for smartystreets zipcode
            if service == SMARTYSTREETS_SERVICE and postal_only:
                result.service = SMARTYSTEETS_ZIPCODE_SERVICE

        except geopy.exc.GeocoderTimedOut:
            result = Location()
            result.service = "Timeout"
        return result

    def reverse(self, latlon):
        if type(latlon) == tuple:
            lat = latlon[0]
            lon = latlon[1]
        else:
            try:
                (lat, lon) = latlon.split(',')
            except ValueError:
                raise ValueError('unable to parse latlon as either tuple or comma delimited string')
        located = Location(self.client.reverse((lat, lon)))
        located.service = self.get_service_name()
        return located


# separate Smartystreets API endpoint for US Zipcodes
# should probably be sent upstream to geopy, but they aren't good at taking PRs

class SmartystreetsUSZipcode(geopy.geocoders.LiveAddress):
    def __init__(self, auth_id, auth_token):
        super(SmartystreetsUSZipcode, self).__init__(auth_id, auth_token)
        self.api = 'https://us-zipcode.api.smartystreets.com/lookup'

    def _compose_url(self, zipcode):
        query = {
            'auth-id': self.auth_id,
            'auth-token': self.auth_token,
            'zipcode': zipcode
        }
        return '{url}?{query}'.format(url=self.api, query=geopy.compat.urlencode(query))

    @staticmethod
    def _format_structured_address(matches):
        if matches.get('zipcodes'):
            best_match = matches.get('zipcodes')[0]
        else:
            return None
        latitude = best_match.get('latitude')
        longitude = best_match.get('longitude')
        return Location(
            address=best_match.get('zipcode'),
            point=(latitude, longitude) if latitude and longitude else None,
            raw=best_match
        )
