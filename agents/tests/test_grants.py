import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grants  # noqa: E402


class GrantStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-grants-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'docs').mkdir()
        self.state = self.root / 'places.json'

    def test_grant_upgrade_revoke_lifecycle(self):
        grants.grant(self.root / 'docs', 'read', state_path=self.state)
        [first] = grants.list_grants(self.state)
        self.assertEqual((first['access'], first['source']), ('read', 'cli'))
        self.assertTrue(first['id'] and first['granted_at'])
        grants.grant(self.root / 'docs', 'write', state_path=self.state)
        [upgraded] = grants.list_grants(self.state)
        self.assertEqual(upgraded['access'], 'write')
        self.assertEqual(grants.revoke(upgraded['id'], state_path=self.state), [])
        self.assertEqual(grants.list_grants(self.state), [])

    def test_revoke_by_path_and_unknown_ref(self):
        grants.grant(self.root / 'docs', state_path=self.state)
        self.assertEqual(grants.revoke(str(self.root / 'docs'), state_path=self.state), [])
        with self.assertRaises(SystemExit):
            grants.revoke('nope', state_path=self.state)

    def test_grant_rejects_non_directories(self):
        with self.assertRaises(SystemExit):
            grants.grant(self.root / 'missing', state_path=self.state)
        with self.assertRaises(SystemExit):
            grants.grant(self.root / 'docs', access='admin', state_path=self.state)

    def test_legacy_entries_normalize_to_read(self):
        self.state.write_text(json.dumps({'grants': [{'path': str(self.root / 'docs')}]}))
        [legacy] = grants.list_grants(self.state)
        self.assertEqual((legacy['access'], legacy['source']), ('read', 'legacy'))

    def test_cli_round_trip(self):
        run = lambda *a: subprocess.run(
            [sys.executable, str(Path(grants.__file__)), '--state', str(self.state), *a],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(run('grant', str(self.root / 'docs'), '--access', 'write').returncode, 0)
        listed = run('list')
        self.assertIn('write', listed.stdout)
        self.assertIn('docs', listed.stdout)
        self.assertEqual(run('revoke', str(self.root / 'docs')).returncode, 0)
        self.assertIn('no folder grants', run('list').stdout)


if __name__ == '__main__':
    unittest.main()
