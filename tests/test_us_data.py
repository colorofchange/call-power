import logging

from run import BaseTestCase

from call_server.political_data.lookup import locate_targets
from call_server.political_data.countries.us import USDataProvider
from call_server.political_data.geocode import Location
from call_server.campaign.models import Campaign, Target
from call_server.campaign.constants import (
    INCLUDE_SPECIAL_BEFORE, INCLUDE_SPECIAL_AFTER,
    INCLUDE_SPECIAL_ONLY, INCLUDE_SPECIAL_FIRST
)


class TestUSData(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        # quiet logging
        logging.getLogger('cache').setLevel(logging.WARNING)
        logging.getLogger(__name__).setLevel(logging.WARNING)

        cls.mock_cache = {}  # mock flask-cache outside of application context
        cls.us_data = USDataProvider(cls.mock_cache, 'localmem')
        cls.us_data.load_data()


    def setUp(self, **kwargs):
        super(TestUSData, self).setUp(**kwargs)

        self.CONGRESS_CAMPAIGN = Campaign(
            country_code='us',
            campaign_type='congress',
            campaign_subtype='both',
            target_ordering='in-order',
            locate_by='postal')

        # avoid geocoding round-trip
        self.mock_location = Location('Boston, MA', (42.355662,-71.065483),
            {'state':'MA','zipcode':'02111'})

        self.mock_location_split_parties = Location('Bakersfield, CA', (35.375960, -119.020865),
            {'state':'MA','zipcode':'93301'})

       # this zipcode pretty evenly split between KY-2 & TN-7
        self.mock_location_multiple_states = Location('Fort Campbell, KY', (36.647207, -87.451635),
            {'state':'KY','zipcode':'42223'})

        # this zipcode pretty evenly split between WI-2 & WI-3
        self.mock_location_multiple_districts = Location('Hazel Green, WI', (42.532498, -90.436727),
            {'state':'WI','zipcode':'53811'})

    def test_cache(self):
        self.assertIsNotNone(self.mock_cache)
        self.assertIsNotNone(self.us_data)

    def test_districts(self):
        district = self.us_data.get_districts('94612')[0]
        self.assertEqual(district['state'], 'CA')
        self.assertEqual(district['house_district'], '13')

    def test_district_multiple(self):
        districts = self.us_data.get_districts('53811')
        self.assertEqual(len(districts), 2)

    def test_district_state_lines(self):
        districts = self.us_data.get_districts('42223')
        self.assertEqual(len(districts), 2)

    def test_senate(self):
        senator_0 = self.us_data.get_senators('CA')[0]
        self.assertEqual(senator_0['chamber'], 'senate')
        self.assertEqual(senator_0['state'], 'CA')
        self.assertGreater(len(senator_0['offices']), 1)

        senator_1 = self.us_data.get_senators('CA')[1]
        self.assertEqual(senator_1['chamber'], 'senate')
        self.assertEqual(senator_1['state'], 'CA')
        self.assertGreater(len(senator_1['offices']), 1)

        # make sure we got two different senators...
        self.assertNotEqual(senator_0['last_name'], senator_1['last_name'])

    def test_house(self):
        rep = self.us_data.get_house_members('CA', '13')[0]
        self.assertEqual(rep['chamber'], 'house')
        self.assertEqual(rep['state'], 'CA')
        self.assertEqual(rep['district'], '13')
        self.assertGreater(len(rep['offices']), 1)

    def test_dc(self):
        no_senators = self.us_data.get_senators('DC')
        self.assertEqual(no_senators, [])

        rep = self.us_data.get_house_members('DC', '0')[0]
        self.assertEqual(rep['chamber'], 'house')
        self.assertEqual(rep['state'], 'DC')
        self.assertEqual(rep['district'], '0')
        self.assertGreater(len(rep['offices']), 1)

    def test_locate_targets(self):
        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        # returns a list of target uids
        self.assertEqual(len(uids), 3)

        house_rep = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(house_rep['chamber'], 'house')
        self.assertEqual(house_rep['state'], 'MA')

        senator_0 = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(senator_0['chamber'], 'senate')
        self.assertEqual(senator_0['state'], 'MA')

        senator_1 = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(senator_1['chamber'], 'senate')
        self.assertEqual(senator_1['state'], 'MA')

    def test_locate_targets_house_only(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'lower'
        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')

    def test_locate_targets_senate_only(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'upper'

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 2)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'senate')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'senate')

    def test_locate_targets_both_ordered_house_first(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'both'
        self.CONGRESS_CAMPAIGN.target_ordering = 'lower-first'

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'senate')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'senate')

    def test_locate_targets_both_ordered_senate_first(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'both'
        self.CONGRESS_CAMPAIGN.target_ordering = 'upper-first'

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'senate')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'senate')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'house')

    def test_locate_targets_both_ordered_democrats_first(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'both'
        self.CONGRESS_CAMPAIGN.target_ordering = 'democrats-first'

        uids = locate_targets(self.mock_location_split_parties, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['party'], 'Democrat')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['party'], 'Democrat')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['party'], 'Republican')

    def test_locate_targets_both_ordered_republicans_first(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'both'
        self.CONGRESS_CAMPAIGN.target_ordering = 'republicans-first'

        uids = locate_targets(self.mock_location_split_parties, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['party'], 'Republican')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['party'], 'Democrat')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['party'], 'Democrat')


    def test_locate_targets_multiple_states(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'both'
        self.CONGRESS_CAMPAIGN.target_ordering = 'lower-first'

        uids = locate_targets(self.mock_location_multiple_states, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 6)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')
        self.assertEqual(first['state'], 'KY')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'house')
        self.assertEqual(second['state'], 'TN')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'senate')
        self.assertEqual(third['state'], 'TN')

        fourth = self.us_data.get_uid(uids[3])[0]
        self.assertEqual(fourth['chamber'], 'senate')
        self.assertEqual(fourth['state'], 'TN')

        fifth = self.us_data.get_uid(uids[4])[0]
        self.assertEqual(fifth['chamber'], 'senate')
        self.assertEqual(fifth['state'], 'KY')

        sixth = self.us_data.get_uid(uids[5])[0]
        self.assertEqual(sixth['chamber'], 'senate')
        self.assertEqual(sixth['state'], 'KY')  
 

    def test_locate_targets_multiple_districts(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'both'
        self.CONGRESS_CAMPAIGN.target_ordering = 'lower-first'

        uids = locate_targets(self.mock_location_multiple_districts, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 4)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')
        self.assertEqual(first['state'], 'WI')
        self.assertEqual(first['district'], '2')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'house')
        self.assertEqual(second['state'], 'WI')
        self.assertEqual(second['district'], '3')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'senate')
        self.assertEqual(third['state'], 'WI')

        fourth = self.us_data.get_uid(uids[3])[0]
        self.assertEqual(third['chamber'], 'senate')
        self.assertEqual(fourth['state'], 'WI')

    def test_locate_targets_special_before(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'upper'

        (special_target, created) = Target.get_or_create('us:bioguide:S000033', cache=self.mock_cache) # Bernie
        self.CONGRESS_CAMPAIGN.target_set = [special_target,]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_BEFORE

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'senate')
        self.assertEqual(first['last_name'], 'Sanders')
        self.assertEqual(first['state'], 'VT')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'senate')
        self.assertEqual(second['state'], 'MA')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'senate')
        self.assertEqual(third['state'], 'MA')

    def test_locate_targets_special_after(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'upper'

        (special_target, created) = Target.get_or_create('us:bioguide:S000033', cache=self.mock_cache) # Bernie
        self.CONGRESS_CAMPAIGN.target_set = [special_target,]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_AFTER

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'senate')
        self.assertEqual(first['state'], 'MA')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'senate')
        self.assertEqual(second['state'], 'MA')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'senate')
        self.assertEqual(third['state'], 'VT')
        self.assertEqual(third['last_name'], 'Sanders')

    def test_locate_targets_special_only_in_location(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'upper'

        (special_target, created) = Target.get_or_create('us:bioguide:W000817', cache=self.mock_cache) # Warren
        self.CONGRESS_CAMPAIGN.target_set = [special_target,]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_ONLY

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'senate')
        self.assertEqual(first['last_name'], 'Warren')
        self.assertEqual(first['state'], 'MA')

    def test_locate_targets_special_only_in_location_district_office(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'upper'

        (special_target, created) = Target.get_or_create('us:bioguide:W000817-woburn', cache=self.mock_cache) # Warren
        self.CONGRESS_CAMPAIGN.target_set = [special_target,]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_ONLY

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'senate')
        self.assertEqual(first['last_name'], 'Warren')
        self.assertEqual(first['state'], 'MA')

    def test_locate_targets_special_only_outside_location(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'upper'

        (special_target, created) = Target.get_or_create('us:bioguide:S000033', cache=self.mock_cache) # Bernie
        self.CONGRESS_CAMPAIGN.target_set = [special_target,]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_ONLY

        # mock_location is outside of special targets
        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 0)

    def test_locate_targets_special_multiple_before(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'lower'

        (special_target_one, created_one) = Target.get_or_create('us:bioguide:P000197', cache=self.mock_cache) # Pelosi
        (special_target_two, created_two) = Target.get_or_create('us:bioguide:R000570', cache=self.mock_cache) # Ryan
        self.CONGRESS_CAMPAIGN.target_set = [special_target_one, special_target_two]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_BEFORE

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')
        self.assertEqual(first['last_name'], 'Pelosi')
        self.assertEqual(first['state'], 'CA')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'house')
        self.assertEqual(second['last_name'], 'Ryan')
        self.assertEqual(second['state'], 'WI')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'house')
        self.assertEqual(third['state'], 'MA')
 
    def test_locate_targets_special_multiple_after(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'lower'

        (special_target_one, created_one) = Target.get_or_create('us:bioguide:P000197', cache=self.mock_cache) # Pelosi
        (special_target_two, created_two) = Target.get_or_create('us:bioguide:R000570', cache=self.mock_cache) # Ryan
        self.CONGRESS_CAMPAIGN.target_set = [special_target_one, special_target_two]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_AFTER

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')
        self.assertEqual(first['state'], 'MA')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'house')
        self.assertEqual(second['last_name'], 'Pelosi')
        self.assertEqual(second['state'], 'CA')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'house')
        self.assertEqual(third['last_name'], 'Ryan')
        self.assertEqual(third['state'], 'WI')

    def test_locate_targets_special_multiple_only(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'lower'

        (special_target_one, created_one) = Target.get_or_create('us:bioguide:P000197', cache=self.mock_cache) # Pelosi
        (special_target_two, created_two) = Target.get_or_create('us:bioguide:R000570', cache=self.mock_cache) # Ryan
        (special_target_three, created_three) = Target.get_or_create('us:bioguide:C001037', cache=self.mock_cache) # Capuano
        self.CONGRESS_CAMPAIGN.target_set = [special_target_one, special_target_two, special_target_three]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_ONLY

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 1)

        # should only get overlap between special and location
        # in this case, just Capuano

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')
        self.assertEqual(first['state'], 'MA')

    def test_locate_targets_special_multiple_first(self):
        self.CONGRESS_CAMPAIGN.campaign_subtype = 'lower'

        (special_target_one, created_one) = Target.get_or_create('us:bioguide:P000197', cache=self.mock_cache) # Pelosi
        (special_target_two, created_two) = Target.get_or_create('us:bioguide:R000570', cache=self.mock_cache) # Ryan
        (special_target_three, created_three) = Target.get_or_create('us:bioguide:C001037', cache=self.mock_cache) # Capuano
        self.CONGRESS_CAMPAIGN.target_set = [special_target_one, special_target_two, special_target_three]
        self.CONGRESS_CAMPAIGN.include_special = INCLUDE_SPECIAL_FIRST

        uids = locate_targets(self.mock_location, self.CONGRESS_CAMPAIGN, cache=self.mock_cache)
        self.assertEqual(len(uids), 3)

        # should get targets in order, with location match first

        first = self.us_data.get_uid(uids[0])[0]
        self.assertEqual(first['chamber'], 'house')
        self.assertEqual(first['state'], 'MA')

        second = self.us_data.get_uid(uids[1])[0]
        self.assertEqual(second['chamber'], 'house')
        self.assertEqual(second['state'], 'CA')

        third = self.us_data.get_uid(uids[2])[0]
        self.assertEqual(third['chamber'], 'house')
        self.assertEqual(third['state'], 'WI')
