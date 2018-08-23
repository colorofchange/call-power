import logging

from run import BaseTestCase

from call_server.political_data.lookup import locate_targets
from call_server.political_data.countries.us import USDataProvider
from call_server.political_data.constants import US_STATES
from call_server.political_data.geocode import Location
from call_server.campaign.models import Campaign

class TestUSStateData(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        # quiet logging
        logging.getLogger('cache').setLevel(logging.WARNING)
        logging.getLogger(__name__).setLevel(logging.WARNING)

        cls.mock_cache = {}  # mock flask-cache outside of application context
        cls.us_data = USDataProvider(cls.mock_cache, 'localmem')
        cls.us_data.load_data()

    def setUp(self, **kwargs):
        super(TestUSStateData, self).setUp(**kwargs)

        self.STATE_CAMPAIGN = Campaign(
            country_code='us',
            campaign_type='state',
            campaign_subtype='both',
            target_ordering='in-order',
            locate_by='latlon')

        self.mock_location = Location('Oakland, CA', (37.804417,-122.267747),
            {'state':'CA','zipcode':'94612'})

    def test_cache(self):
        self.assertIsNotNone(self.mock_cache)
        self.assertIsNotNone(self.us_data)

    def test_locate_targets(self):
        uids = locate_targets(self.mock_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        # returns a list of uids (openstates leg_id)
        self.assertEqual(len(uids), 2)

        house_rep = self.us_data.get_uid(uids[0])
        self.assertEqual(house_rep['chamber'], 'lower')
        self.assertEqual(house_rep['state'].upper(), 'CA')
        self.assertEqual(house_rep['active'], True)

        senator = self.us_data.get_uid(uids[1])
        self.assertEqual(senator['chamber'], 'upper')
        self.assertEqual(senator['state'].upper(), 'CA')
        self.assertEqual(senator['active'], True)

    def test_locate_targets_lower_only(self):
        self.STATE_CAMPAIGN.campaign_subtype = 'lower'
        uids = locate_targets(self.mock_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)

        house_rep = self.us_data.get_uid(uids[0])
        self.assertEqual(house_rep['chamber'], 'lower')
        self.assertEqual(house_rep['state'].upper(), 'CA')
        self.assertEqual(house_rep['active'], True)

    def test_locate_targets_upper_only(self):
        self.STATE_CAMPAIGN.campaign_subtype = 'upper'
        uids = locate_targets(self.mock_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)

        senator = self.us_data.get_uid(uids[0])
        self.assertEqual(senator['chamber'], 'upper')
        self.assertEqual(senator['state'].upper(), 'CA')
        self.assertEqual(senator['active'], True)

    def test_locate_targets_ordered_lower_first(self):
        self.STATE_CAMPAIGN.campaign_subtype = 'both'
        self.STATE_CAMPAIGN.target_ordering = 'lower-first'
        uids = locate_targets(self.mock_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 2)

        first = self.us_data.get_uid(uids[0])
        self.assertEqual(first['chamber'], 'lower')

        second = self.us_data.get_uid(uids[1])
        self.assertEqual(second['chamber'], 'upper')

    def test_locate_targets_ordered_upper_first(self):
        self.STATE_CAMPAIGN.campaign_subtype = 'both'
        self.STATE_CAMPAIGN.target_ordering = 'upper-first'
        uids = locate_targets(self.mock_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 2)

        first = self.us_data.get_uid(uids[0])
        self.assertEqual(first['chamber'], 'upper')

        second = self.us_data.get_uid(uids[1])
        self.assertEqual(second['chamber'], 'lower')

    def test_locate_targets_incorrect_state(self):
        self.STATE_CAMPAIGN.campaign_state = 'CA'

        other_location = Location('Boston, MA', (42.355662,-71.065483),
            {'components':{'state':'MA','zipcode':'02111'}})
        
        uids = locate_targets(other_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 0)

    def test_get_state_legid(self):
        # uses openstates api directly, not our locate_targets functions
        self.STATE_CAMPAIGN.campaign_state = 'CA'

        legids = self.us_data.get_state_legislators(self.mock_location)
        self.assertEqual(len(legids), 2)

        first = self.us_data.get_state_legid(legids[0]['id'])
        self.assertEqual(first['chamber'], 'upper')

        second = self.us_data.get_state_legid(legids[1]['id'])
        self.assertEqual(second['chamber'], 'lower')

    def test_50_governors(self):
        NO_GOV = ['AS', 'GU', 'MP', 'PR', 'VI', 'DC', '']
        for (abbr, state_name) in US_STATES:
            gov = self.us_data.get_state_governor(abbr)
            if not gov:
                self.assertIn(abbr, NO_GOV)
                continue
            self.assertEqual(gov[0]['title'], 'Governor')
            self.assertEqual(gov[0]['state'], abbr)
            self.assertEqual(gov[0]['state_name'], state_name)

    def test_ca_governor(self):
        gov = self.us_data.get_state_governor('CA')[0]
        self.assertEqual(gov['first_name'], 'Jerry')
        self.assertEqual(gov['last_name'], 'Brown')
        self.assertEqual(gov['state'], 'CA')
        self.assertEqual(gov['state_name'], 'California')
        self.assertEqual(gov['phone'], '916-445-2841')

    def test_locate_targets_gov(self):
        self.STATE_CAMPAIGN.campaign_subtype = 'exec'
        uids = locate_targets(self.mock_location, self.STATE_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)
        
        gov = self.us_data.get_uid(uids[0])
        self.assertEqual(gov[0]['state'], 'CA')
        self.assertEqual(gov[0]['state_name'], 'California')
        self.assertEqual(gov[0]['title'], 'Governor')

