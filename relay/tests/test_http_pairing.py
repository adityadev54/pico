"""Pairing over real HTTP (A11): the actual relay handler on localhost
with a fake Supabase transport. Proves authorize -> pair -> heartbeat ->
authorized tools -> revoke -> unpaired, plus the code grant/deny matrix.
"""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from relay.app import make_handler
from relay.service import PicoService, digest
from relay.state import RelayState
from relay.tests.fake import FakeSupabase


class HttpPairingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-http-')
        self.addCleanup(self.tmp.cleanup)
        self.db = FakeSupabase()
        service = PicoService(self.db, RelayState(Path(self.tmp.name) / 's.sqlite'))
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def shutdown(self):
        self.server.shutdown()
        self.thread.join(timeout=10)
        self.server.server_close()

    def post(self, path, body, token=None):
        request = urllib.request.Request(
            self.base + path, data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json',
                     **({'Authorization': 'Bearer ' + token} if token else {})})
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b'{}')

    def test_pair_poll_revoke_journey(self):
        status, pairing = self.post('/pairing', {}, 'user-token')
        self.assertEqual(status, 200)
        self.assertRegex(pairing['code'], r'^\d{6}$')
        status, claimed = self.post('/claim', {'code': pairing['code'], 'os': 'macos',
                                               'name': 'Test Mac'}, None)
        self.assertEqual(status, 200)
        device_token = claimed['token']
        status, poll = self.post('/agent/poll', {}, device_token)
        self.assertEqual(status, 200)
        self.assertEqual(poll['device_id'], claimed['device_id'])
        row = self.db.db('devices', {'id': 'eq.' + claimed['device_id']})[0]
        seen = datetime.fromisoformat(row['last_seen'])
        self.assertLess((datetime.now(timezone.utc) - seen).total_seconds(), 60)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post('/pairing', {}, 'user-token')
        self.assertEqual(ctx.exception.code, 409)
        status, _ = self.post('/agent/revoke', {}, device_token)
        self.assertEqual(status, 200)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post('/agent/poll', {}, device_token)
        self.assertEqual(ctx.exception.code, 401)
        status, fresh = self.post('/pairing', {}, 'user-token')
        self.assertEqual(status, 200)
        self.assertRegex(fresh['code'], r'^\d{6}$')

    def test_code_grant_deny_matrix(self):
        _, pairing = self.post('/pairing', {}, 'user-token')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post('/claim', {'code': '000000', 'os': 'macos'}, None)
        self.assertEqual(ctx.exception.code, 400)
        _, claimed = self.post('/claim', {'code': pairing['code'], 'os': 'macos'}, None)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post('/claim', {'code': pairing['code'], 'os': 'macos'}, None)
        self.assertEqual(ctx.exception.code, 400)
        expired_code = '123456'
        self.db.tables['pairing_codes'].append({
            'code_hash': digest('pico:' + expired_code), 'user_id': 'owner-1',
            'expires_at': (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            'claimed_at': None})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post('/claim', {'code': expired_code, 'os': 'macos'}, None)
        self.assertEqual(ctx.exception.code, 400)

    def test_cancel_route_returns_receipt(self):
        _, pairing = self.post('/pairing', {}, 'user-token')
        _, claimed = self.post('/claim', {'code': pairing['code'], 'os': 'macos'}, None)
        status, task = self.post('/tasks', {'device_id': claimed['device_id'],
                                            'kind': 'find_document',
                                            'input': {'query': 'brief'}}, 'user-token')
        self.assertEqual(status, 200)
        status, receipt = self.post('/tasks/cancel', {'id': task['id']}, 'user-token')
        self.assertEqual(status, 200)
        self.assertEqual((receipt['removed_queued'], receipt['notified_helper']), (1, True))

    def test_upload_route_returns_stable_artifact(self):
        import base64
        _, pairing = self.post('/pairing', {}, 'user-token')
        _, claimed = self.post('/claim', {'code': pairing['code'], 'os': 'macos'}, None)
        body = {'device_id': claimed['device_id'], 'name': 'photo.jpg',
                'content_base64': base64.b64encode(b'fake-jpg-bytes').decode(),
                'purpose': 'transfer'}
        status, first = self.post('/uploads', body, 'user-token')
        self.assertEqual(status, 200)
        self.assertRegex(first['artifact_id'], r'^[0-9a-f]{64}$')
        self.assertFalse(first['duplicate'])
        status, second = self.post('/uploads', body, 'user-token')
        self.assertEqual(status, 200)
        self.assertTrue(second['duplicate'])
        self.assertEqual(second['artifact_id'], first['artifact_id'])

    def test_lockout_after_five_bad_codes(self):
        for _ in range(5):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                self.post('/claim', {'code': 'not-a-code', 'os': 'macos'}, None)
            self.assertEqual(ctx.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post('/claim', {'code': '000000', 'os': 'macos'}, None)
        self.assertEqual(ctx.exception.code, 429)


if __name__ == '__main__':
    unittest.main()
