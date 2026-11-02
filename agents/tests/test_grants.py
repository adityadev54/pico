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

    def test_record_builds_a_grant_without_io(self):
        entry = grants.record(self.root / 'docs', 'read', 'approval')
        self.assertEqual(
            (entry['path'], entry['access'], entry['source']),
            (str((self.root / 'docs').resolve()), 'read', 'approval'))
        self.assertTrue(entry['id'] and entry['granted_at'])
        with self.assertRaises(SystemExit):
            grants.record(self.root / 'missing', 'read', 'approval')

    def test_repair_keeps_folder_and_app_approvals(self):
        state = {'places': {'p': {}}, 'outgoing': [{'id': 'm'}],
                 'handled': ['m'], 'task_journal': {'m': {}},
                 'grants': [{'path': str(self.root / 'docs'), 'access': 'write'}],
                 'allowed_apps': [{'id': 'a', 'name': 'Safari'}],
                 'character': 'tuck'}
        fresh = grants.fresh_pair_state(state)
        self.assertEqual(fresh['grants'], state['grants'])
        self.assertEqual(fresh['allowed_apps'], state['allowed_apps'])
        self.assertEqual(
            (fresh['places'], fresh['outgoing'], fresh['handled'], fresh['task_journal']),
            ({}, [], [], {}))
        self.assertEqual(fresh['character'], 'tuck')
        self.assertEqual(state['places'], {'p': {}})
        with self.assertRaises(SystemExit):
            grants.grant(self.root / 'docs', access='admin', state_path=self.state)

    def test_delete_level_grants_and_lists(self):
        grants.grant(self.root / 'docs', 'delete', state_path=self.state)
        [entry] = grants.list_grants(self.state)
        self.assertEqual(entry['access'], 'delete')
        from native_search import granted_roots
        roots = [{'path': str(self.root / 'docs'), 'access': 'delete'}]
        self.assertTrue(granted_roots(roots, 'delete'))
        self.assertTrue(granted_roots(roots, 'write'))
        self.assertTrue(granted_roots(roots))
        self.assertFalse(granted_roots(
            [{'path': str(self.root / 'docs'), 'access': 'write'}], 'delete'))

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

    def test_merge_grants_adopts_disk_without_dropping_memory(self):
        memory = [{'id': 'm1', 'path': '/tmp/a', 'access': 'read',
                   'source': 'approval'}]
        disk = [{'id': 'd1', 'path': '/tmp/a', 'access': 'write',
                 'source': 'cli'},
                {'id': 'd2', 'path': '/tmp/b', 'access': 'read',
                 'source': 'popup-approval'},
                {'path': '/tmp/c'},
                'junk',
                {'path': '/tmp/d', 'access': 'owner'}]
        merged = grants.merge_grants(memory, disk)
        by_path = {entry['path']: entry for entry in merged}
        self.assertEqual(set(by_path), {'/tmp/a', '/tmp/b', '/tmp/c'})
        self.assertEqual(by_path['/tmp/a']['access'], 'write')
        self.assertEqual(by_path['/tmp/a']['id'], 'm1')
        self.assertEqual(by_path['/tmp/a']['source'], 'cli')
        self.assertEqual(by_path['/tmp/b']['source'], 'popup-approval')
        self.assertEqual(by_path['/tmp/c']['access'], 'read')
        self.assertEqual(grants.merge_grants(memory, []), memory)
        adopted = grants.merge_grants([], disk)
        self.assertEqual([entry['path'] for entry in adopted],
                         ['/tmp/a', '/tmp/b', '/tmp/c'])
        self.assertEqual(adopted[0]['access'], 'write')
        self.assertEqual(adopted[1]['id'], 'd2')


if __name__ == '__main__':
    unittest.main()
