import json
import sys
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agents'))
from app_access import catalog, open_selected
from companion import Companion
from relay.app_messages import app_payload


class AppAccessTests(unittest.TestCase):
    def setUp(self):
        self.identity = str(uuid.uuid4())
        self.request = str(uuid.uuid4())
        self.state = {'allowed_apps': [{'id': self.identity, 'name': 'Test App', 'bundle': 'local.pico.test'}]}
        self.launched = []
        self.platform = SimpleNamespace(open_app=lambda bundle: self.launched.append(bundle) or True)

    def test_only_selected_ids_can_open(self):
        self.assertFalse(open_selected(self.state, '/bin/sh', self.platform)[0])
        self.assertEqual(self.launched, [])
        self.assertTrue(open_selected(self.state, self.identity, self.platform)[0])
        self.assertEqual(self.launched, ['local.pico.test'])

    def test_revoked_and_expired_grants_do_not_launch(self):
        self.assertFalse(open_selected(self.state, self.identity, self.platform, '0')[0])
        self.state['allowed_apps'] = []
        self.assertFalse(open_selected(self.state, self.identity, self.platform)[0])
        self.assertEqual(self.launched, [])

    def test_catalog_contains_no_local_identity_or_paths(self):
        payload = catalog(self.state)
        self.assertNotIn('bundle', payload['catalog'])
        self.assertNotIn('path', payload['catalog'])
        self.assertEqual(json.loads(payload['catalog']), [{'id': self.identity, 'name': 'Test App'}])
        app_payload('app_catalog', payload)

    def test_server_supplies_expiry_and_rejects_remote_paths(self):
        message = app_payload('open_app', {'app_id': self.identity, 'request_id': self.request})
        self.assertIn('expires_at', message)
        with self.assertRaises(ValueError):
            app_payload('open_app', {'app_id': self.identity, 'request_id': self.request, 'path': '/bin/sh'})
        with self.assertRaises(ValueError):
            app_payload('app_catalog', {'catalog': json.dumps([{'id': self.identity, 'name': 'App', 'path': '/Applications/App.app'}])})

    def test_capture_rechecks_exclusions_after_foreground_changes(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'home', return_value=Path(folder)):
            helper = Companion.__new__(Companion)
            helper.lock = threading.RLock()
            helper.state = {'places': {}, 'outgoing': [], 'snapshots': True, 'excluded_apps': [{'bundle': 'private.app'}]}
            calls = []
            def capture(path, excluded):
                calls.append(excluded)
                return {'snapshot_saved': False, 'bundle': 'private.app'}
            helper.platform = SimpleNamespace(context=capture)
            helper.save = lambda: None
            helper.hold_context({'app': 'Allowed', 'bundle': 'allowed.app', 'screen_access': True})
            self.assertEqual(calls, [['private.app']])
            self.assertIsNone(next(iter(helper.state['places'].values()))['snapshot'])

    def test_snapshot_tracks_actual_captured_app(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'home', return_value=Path(folder)):
            helper = Companion.__new__(Companion); helper.lock = threading.RLock()
            helper.state = {'places': {}, 'outgoing': [], 'snapshots': True, 'excluded_apps': []}
            helper.platform = SimpleNamespace(context=lambda path, excluded: {'snapshot_saved': True, 'bundle': 'actual.app', 'app': 'Actual'})
            helper.save = lambda: None
            helper.hold_context({'app': 'Earlier', 'bundle': 'earlier.app', 'screen_access': True})
            self.assertEqual(next(iter(helper.state['places'].values()))['bundle'], 'actual.app')

    def test_excluded_foreground_app_never_calls_capture(self):
        helper = Companion.__new__(Companion); helper.lock = threading.RLock()
        helper.state = {'places': {}, 'outgoing': [], 'snapshots': True, 'excluded_apps': [{'bundle': 'private.app'}]}
        def forbidden(*args): raise AssertionError('Excluded app was captured')
        helper.platform = SimpleNamespace(context=forbidden); helper.save = lambda: None
        helper.hold_context({'app': 'Private', 'bundle': 'private.app', 'screen_access': True})
        self.assertIsNone(next(iter(helper.state['places'].values()))['snapshot'])


if __name__ == '__main__': unittest.main()
