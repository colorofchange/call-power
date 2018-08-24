import logging
import json, yaml

from run import BaseTestCase

from call_server.political_data.adapters import adapt_by_key
from call_server.political_data.countries.us import USDataProvider
from call_server.political_data.countries.ca import CADataProvider

class TestDataAdapters(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self, **kwargs):
        super(TestDataAdapters, self).setUp(**kwargs)

    def test_us_adapter(self):
        f = open('tests/data/us_congress_representative.yaml', 'r')
        data = yaml.load(f.read())[0]
        f.close()

        data['bioguide_id'] = data['id']['bioguide']
        data['first_name'] = data['name']['first']
        data['last_name'] = data['name']['last']
        data['phone'] = data['terms'][0]['phone']
        data['title'] = "Senator" if data['terms'][0]['type'] == "sen" else "Representative"

        data_provider = USDataProvider({})
        key = data_provider.KEY_BIOGUIDE.format(**data)

        adapter = adapt_by_key(key)
        target = adapter.target(data)
        target['offices'] = adapter.offices(data)

        self.assertEqual(target['uid'], data['id']['bioguide'])
        self.assertEqual(target['name'], data['name']['official_full'])
        self.assertEqual(target['title'], 'Representative')
        self.assertEqual(target['number'], data['phone'])
        self.assertEqual(target['offices'][0]['number'], data['offices'][0]['phone'])
        self.assertEqual(target['offices'][0]['type'], 'district')
    
    def test_usstate_adapter(self):
        f = open('tests/data/openstates_representative.json', 'r')
        data = json.loads(f.read())[0]
        f.close()

        data_provider = USDataProvider({})
        key = data_provider.KEY_OPENSTATES.format(**data)

        adapter = adapt_by_key(key)
        target = adapter.target(data)
        target['offices'] = adapter.offices(data)

        self.assertEqual(target['uid'], data['id'])
        self.assertEqual(target['name'], data['full_name'])
        self.assertEqual(target['title'], 'Senator')
        self.assertEqual(target['number'], data['offices'][0]['phone'])
        self.assertEqual(target['offices'][0]['number'], data['offices'][1]['phone'])
        self.assertEqual(target['offices'][0]['type'], 'district')

    def test_opennorth_adapter(self):
        f = open('tests/data/opennorth_representative.json', 'r')
        data = json.loads(f.read(), strict=False)[0]
        # load json with strict=False to avoid ValueError with the unicode parsing
        f.close()

        data_provider = CADataProvider({})
        boundary = data_provider.boundary_url_to_key(data['related']['boundary_url'])
        key = data_provider.KEY_OPENNORTH.format(boundary=boundary)
        data['cache_key'] = key
        adapter = adapt_by_key(key)

        target = adapter.target(data)
        target['offices'] = adapter.offices(data)

        self.assertEqual(target['uid'], key)
        self.assertEqual(target['name'], data['name'])
        self.assertEqual(target['title'], data['elected_office'])
        self.assertEqual(target['number'], data['offices'][0]['tel'])
        self.assertEqual(target['offices'][0]['number'], data['offices'][1]['tel'])
        self.assertEqual(target['offices'][0]['type'], 'constituency')
