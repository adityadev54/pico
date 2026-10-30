import sqlite3
import tempfile
import unittest
from pathlib import Path

from relay.state import RelayState


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-relay-state-')
        self.addCleanup(self.tmp.cleanup)
        self.state = RelayState(Path(self.tmp.name) / 'state.sqlite')

    def test_ping_leaves_no_residue(self):
        self.assertIsNone(self.state.ping())
        with sqlite3.connect(self.state.path) as db:
            self.assertEqual(db.execute('select count(*) from attempts').fetchone()[0], 0)

    def test_five_bad_attempts_lock_out_then_success_clears(self):
        for _ in range(5):
            self.state.attempt('addr-1')
        self.assertTrue(self.state.blocked('addr-1'))
        self.assertFalse(self.state.blocked('addr-2'))
        self.state.attempt('addr-1', success=True)
        self.assertFalse(self.state.blocked('addr-1'))

    def test_delivery_receipts_round_trip(self):
        self.assertFalse(self.state.received('owner-1', 'mail-1'))
        self.state.delivered('owner-1', 'mail-1')
        self.assertTrue(self.state.received('owner-1', 'mail-1'))
        self.assertFalse(self.state.received('owner-2', 'mail-1'))

    def test_receipts_and_attempts_survive_restart(self):
        self.state.delivered('owner-1', 'mail-1')
        for _ in range(4):
            self.state.attempt('addr-7')
        reopened = RelayState(self.state.path)
        self.assertTrue(reopened.received('owner-1', 'mail-1'))
        self.assertFalse(reopened.blocked('addr-7'))
        reopened.attempt('addr-7')
        self.assertTrue(reopened.blocked('addr-7'))


if __name__ == '__main__':
    unittest.main()
