import logging
from datetime import datetime, timedelta

from run import BaseTestCase

from call_server.utils import utc_now
from call_server.extensions import db
from call_server.admin.models import Blocklist


class TestBlocklist(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        # quiet logging
        logging.getLogger(__name__).setLevel(logging.WARNING)

        cls.user_phone = '510-867-5309'
        cls.user_ip = '18.123.456.789'

        cls.other_phone = '404-123-4567'
        cls.other_ip = '255.255.255.255'

    def setUp(self, **kwargs):
        super(TestBlocklist, self).setUp(**kwargs)

        Blocklist.query.delete()
        db.session.commit()

    def test_no_blocks(self):
        self.assertEqual(Blocklist.active_blocks(), [])

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertFalse(is_blocked)

    def test_phone_block(self):
        b = Blocklist(phone_number=self.user_phone)
        db.session.add(b)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 1)

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)

        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)

        self.assertEqual(b.hits, 1)

    def test_phone_hash_block(self):
        b = Blocklist()
        b.phone_hash = '2ceab7622c3ea1de7e5b1db8c90ed3c161a4d097df6755d21df8a349fe63089c'
        db.session.add(b)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 1)

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)

        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)

        self.assertEqual(b.hits, 1)

    def test_ip_block(self):
        b = Blocklist(ip_address=self.user_ip)
        db.session.add(b)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 1)

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)

        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)

        self.assertEqual(b.hits, 1)


    def test_phone_and_ip_block(self):
        b = Blocklist(phone_number=self.user_phone, ip_address=self.user_ip)
        db.session.add(b)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 1)

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)

        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)

        self.assertEqual(b.hits, 1)

    def test_separate_phone_ip_blocks(self):
        b_phone = Blocklist(phone_number=self.user_phone)
        b_ip = Blocklist(ip_address=self.user_ip)
        db.session.add(b_phone)
        db.session.add(b_ip)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 2)

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)

        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)

        self.assertEqual(b_phone.hits, 1)
        self.assertEqual(b_ip.hits, 1)

    def test_separate_phone_ip_blocks_just_one_matches(self):
        some_other_phone = '800-555-1212'
        some_other_ip = '123.123.255.42'

        b_phone = Blocklist(phone_number=self.user_phone)
        b_ip = Blocklist(ip_address=some_other_ip)
        db.session.add(b_phone)
        db.session.add(b_ip)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 2)

        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)
        self.assertEqual(b_phone.hits, 1)
        self.assertEqual(b_ip.hits, 0)

        someone_else_blocked = Blocklist.user_blocked(some_other_phone, some_other_ip)
        self.assertTrue(someone_else_blocked)
        self.assertEqual(b_phone.hits, 1)
        self.assertEqual(b_ip.hits, 1)    
   
        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)

    def test_block_expires(self):
        one_hour = timedelta(hours=1)
        b = Blocklist(phone_number=self.user_phone, ip_address=self.user_ip)
        b.expires = one_hour

        db.session.add(b)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 1)
        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertTrue(is_blocked)
        self.assertEqual(b.hits, 1)

        # move creation timestamp backwards to expire it
        b.timestamp = b.timestamp - one_hour - timedelta(minutes=2)
        db.session.add(b)
        db.session.commit()

        self.assertEqual(len(Blocklist.active_blocks()), 0)
        is_blocked = Blocklist.user_blocked(self.user_phone, self.user_ip)
        self.assertFalse(is_blocked)

        other_blocked = Blocklist.user_blocked(self.other_phone, self.other_ip)
        self.assertFalse(other_blocked)
        self.assertEqual(b.hits, 1)
