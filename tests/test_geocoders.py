import logging
import json, yaml

from run import BaseTestCase

from call_server.political_data.geocode import LOCAL_USDATA_SERVICE
from call_server.political_data.countries.us import USDataProvider


class TestGeocoders(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_cache = {}  # mock flask-cache outside of application context
        cls.us_data = USDataProvider(cls.mock_cache, 'localmem')
        cls.us_data.load_data()

    def test_cache(self):
        self.assertIsNotNone(self.mock_cache)
        self.assertIsNotNone(self.us_data)

    def test_geocoder_us_zipcode_exists_in_local_cache(self):
        real_zipcode = '94612'
        result = self.us_data._geocoder.postal(real_zipcode, provider=self.us_data)

        self.assertEqual(result.service, LOCAL_USDATA_SERVICE)
        self.assertEqual(result.postal, '94612')
        self.assertEqual(result.state, 'CA')

    def test_geocoder_us_zipcode_exists(self):
        real_zipcode = '94612'
        result = self.us_data._geocoder.postal(real_zipcode)

        self.assertIsNot(result.service, LOCAL_USDATA_SERVICE)
        self.assertEqual(result.postal, '94612')
        self.assertEqual(result.state, 'CA')

    def test_geocoder_us_zipcode_might_exist(self):
        maybe_zipcode = '12345' # business only zipcode, will have to hit the real service
        result = self.us_data._geocoder.postal(maybe_zipcode)

        self.assertEqual(result.postal, '12345')
        # don't assert about state, it's not consistent across geocoders...

    def test_geocoder_us_address_exists(self):
        real_address = '1600 Pennsylvania Ave NW, Washington DC'
        result = self.us_data._geocoder.geocode(real_address)

        self.assertEqual(result.postal, '20500')
        self.assertEqual(result.state, 'DC')
