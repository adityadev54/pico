import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import handlers  # noqa: E402
from native_search import NativeError, candidate_id_for  # noqa: E402
from tools import TOOL_REGISTRY, ToolError  # noqa: E402


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-handlers-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'brief.txt').write_text('hello brief')
        (self.root / 'sub').mkdir()
        self.calls = []
        self.ctx = {
            'task_id': 'task-1',
            'grants': [{'path': str(self.root), 'access': 'write',
                        'id': 'g1', 'granted_at': 't', 'source': 'test'}],
            'transfer': lambda raw, evidence: self.calls.append(('transfer', len(raw))),
            'open_url': lambda url: self.calls.append(('open_url', url)),
            'reopen': lambda bundle: self.calls.append(('reopen', bundle)),
            'notify': lambda: self.calls.append(('notify',)),
        }

    def run_tool(self, tool, args):
        return handlers.dispatch(tool, TOOL_REGISTRY.validate(tool, args), self.ctx)

    def test_search_returns_candidates_with_evidence(self):
        data, evidence = self.run_tool('search_documents', {'query': 'brief'})
        self.assertEqual([c['name'] for c in data['candidates']], ['brief.txt'])
        self.assertIn('digest', data['candidates'][0])
        self.assertEqual(evidence['grant_count'], 1)

    def test_search_miss_raises_typed_error(self):
        with self.assertRaises(NativeError) as ctx:
            self.run_tool('search_documents', {'query': 'zzz-nope'})
        self.assertEqual(ctx.exception.code, 'no_match')

    def test_transfer_posts_bytes_and_returns_excerpt(self):
        cid = candidate_id_for(self.root / 'brief.txt')
        data, evidence = self.run_tool(
            'transfer_selected_file', {'candidate_id': cid, 'approval_id': 'a1'})
        self.assertEqual(self.calls, [('transfer', 11)])
        self.assertEqual(data['name'], 'brief.txt')
        self.assertIn('hello', data['excerpt'])
        self.assertEqual(evidence['candidate_id'], cid)

    def test_read_back_returns_bounded_excerpt(self):
        cid = candidate_id_for(self.root / 'brief.txt')
        data, _ = self.run_tool('read_back_file', {'candidate_id': cid})
        self.assertEqual(data['excerpt'], 'hello brief')

    def test_open_website_and_app_use_injected_side_effects(self):
        data, _ = self.run_tool('open_website', {'url': 'https://example.com/x'})
        self.assertEqual(data, {'url': 'https://example.com/x'})
        data, _ = self.run_tool('open_app', {'app': 'vscode'})
        self.assertEqual(data, {'app': 'vscode'})
        self.assertEqual(self.calls, [('open_url', 'https://example.com/x'),
                                      ('reopen', 'com.microsoft.VSCode')])
        data, _ = self.run_tool('manage_permissions', {})
        self.assertEqual(data, {})
        self.assertIn(('notify',), self.calls)

    def test_fs_list_read_write_round_trip(self):
        data, _ = self.run_tool('fs_list', {})
        self.assertEqual([e['name'] for e in data['entries']], ['brief.txt', 'sub'])
        data, _ = self.run_tool('fs_read', {'path': 'brief.txt'})
        self.assertEqual(data['content'], 'hello brief')
        created, _ = self.run_tool('fs_write', {'path': 'note.txt', 'content': 'v1'})
        self.assertEqual((self.root / 'note.txt').read_text(), 'v1')
        revised, _ = self.run_tool('fs_write', {'path': 'note.txt', 'content': 'v2',
                                                'base_revision': created['digest']})
        self.assertNotEqual(revised['digest'], created['digest'])
        with self.assertRaises(NativeError) as ctx:
            self.run_tool('fs_write', {'path': '../escape.txt', 'content': 'x'})
        self.assertEqual(ctx.exception.code, 'permission_denied')

    def test_process_run_returns_real_result(self):
        import sys as _sys
        data, _ = self.run_tool('process_run', {
            'argv_json': json.dumps([_sys.executable, '-c', 'print(40 + 2)'])})
        self.assertEqual((data['exit_code'], data['stdout']), (0, '42\n'))
        self.assertFalse(data['timed_out'])

    def test_process_run_rejects_bad_invocations(self):
        with self.assertRaises(ToolError):
            self.run_tool('process_run', {'argv_json': 'not json'})
        with self.assertRaises(ToolError):
            self.run_tool('process_run', {'argv_json': '[]'})
        with self.assertRaises(ToolError):
            self.run_tool('process_run', {'argv_json': '["echo"]', 'timeout_s': '999'})

    def test_write_needs_write_grant(self):
        read_only = dict(self.ctx, grants=[{'path': str(self.root), 'access': 'read'}])
        with self.assertRaises(NativeError) as ctx:
            handlers.dispatch('fs_write', {'path': 'n.txt', 'content': 'x'}, read_only)
        self.assertEqual(ctx.exception.code, 'permission_denied')
        self.assertFalse((self.root / 'n.txt').exists())
        data, _ = handlers.dispatch('fs_read', {'path': 'brief.txt'}, read_only)
        self.assertEqual(data['content'], 'hello brief')

    def test_legacy_grant_reads_but_never_writes(self):
        legacy = dict(self.ctx, grants=[{'path': str(self.root)}])
        with self.assertRaises(NativeError):
            handlers.dispatch('fs_write', {'path': 'n.txt', 'content': 'x'}, legacy)
        data, _ = handlers.dispatch('fs_list', {}, legacy)
        self.assertTrue(data['entries'])

    def test_dispatch_rejects_unknown_tool(self):
        with self.assertRaises(ToolError) as ctx:
            handlers.dispatch('wipe_disk', {}, self.ctx)
        self.assertEqual(ctx.exception.code, 'unsupported_tool')

    def test_cancel_registry_lifecycle(self):
        running, cancelled, fired = {}, [], []
        handlers.register_running(running, cancelled, 't1', lambda: fired.append(1))
        self.assertIn('t1', running)
        self.assertIsNone(handlers.note_cancelled(cancelled, running, 't2'))
        stop = handlers.note_cancelled(cancelled, running, 't1')
        self.assertNotIn('t1', running)
        stop()
        self.assertEqual(fired, [1])
        handlers.register_running(running, cancelled, 't1', lambda: fired.append(2))
        self.assertEqual(fired, [1, 2])
        handlers.unregister_running(running, 't1')
        self.assertNotIn('t1', running)
        for i in range(250):
            handlers.note_cancelled(cancelled, running, f't{i}')
        self.assertLessEqual(len(cancelled), 200)

    def test_process_cancel_mid_run(self):
        import sys as _sys
        import threading
        box = {}
        ctx = dict(self.ctx)
        ctx['register_cancel'] = lambda fn: box.setdefault('stop', fn)
        ctx['unregister_cancel'] = lambda: box.pop('stop', None)
        ctx['grants'] = [{'path': str(self.root), 'access': 'write'}]
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(handlers.dispatch(
                'process_run',
                {'argv_json': json.dumps([_sys.executable, '-c',
                                          'import time; time.sleep(30)'])},
                ctx)[0]),
            daemon=True)
        thread.start()
        for _ in range(100):
            if 'stop' in box:
                break
            threading.Event().wait(0.05)
        self.assertIn('stop', box)
        box['stop']()
        thread.join(timeout=15)
        self.assertFalse(thread.is_alive())
        self.assertTrue(result['cancelled'])

    def test_fetch_upload_saves_verified_bytes(self):
        import hashlib
        raw = bytes(range(256)) * 4  # Not valid UTF-8: proves binary path.
        digest = hashlib.sha256(raw).hexdigest()
        ctx = dict(self.ctx, fetch_artifact=lambda aid: raw if aid == digest else b'')
        data, evidence = handlers.dispatch(
            'fetch_upload', TOOL_REGISTRY.validate(
                'fetch_upload', {'artifact_id': digest, 'path': 'photo.jpg'}), ctx)
        self.assertEqual((self.root / 'photo.jpg').read_bytes(), raw)
        self.assertEqual(data['digest'], digest)
        self.assertEqual(evidence['digest'], digest)

    def test_fetch_upload_rejects_tampered_and_resumes_identical(self):
        import hashlib
        from tools import ToolError
        raw = b'\x89PNG-fake-bytes'
        digest = hashlib.sha256(raw).hexdigest()
        ctx = dict(self.ctx, fetch_artifact=lambda aid: raw)
        with self.assertRaises(ToolError) as tampered:
            handlers.dispatch('fetch_upload', TOOL_REGISTRY.validate(
                'fetch_upload', {'artifact_id': '0' * 64, 'path': 'a.png'}), ctx)
        self.assertEqual(tampered.exception.code, 'candidate_changed')
        with self.assertRaises(ToolError):
            handlers.dispatch('fetch_upload', TOOL_REGISTRY.validate(
                'fetch_upload', {'artifact_id': 'not-a-digest', 'path': 'a.png'}), ctx)
        handlers.dispatch('fetch_upload', TOOL_REGISTRY.validate(
            'fetch_upload', {'artifact_id': digest, 'path': 'a.png'}), ctx)
        data, _ = handlers.dispatch('fetch_upload', TOOL_REGISTRY.validate(
            'fetch_upload', {'artifact_id': digest, 'path': 'a.png'}), ctx)
        self.assertTrue(data['duplicate'])
        self.assertEqual((self.root / 'a.png').read_bytes(), raw)
        other = hashlib.sha256(b'different').hexdigest()
        ctx2 = dict(self.ctx, fetch_artifact=lambda aid: b'different')
        with self.assertRaises(NativeError) as conflict:
            handlers.dispatch('fetch_upload', TOOL_REGISTRY.validate(
                'fetch_upload', {'artifact_id': other, 'path': 'a.png'}), ctx2)
        self.assertEqual(conflict.exception.code, 'candidate_changed')
        self.assertEqual((self.root / 'a.png').read_bytes(), raw)

    def test_organize_photos_copies_unique_leaves_originals(self):
        (self.root / 'img1.jpg').write_bytes(b'A' * 100)
        (self.root / 'sub' / 'img2.png').write_bytes(b'B' * 100)
        (self.root / 'sub' / 'dup.jpg').write_bytes(b'A' * 100)
        (self.root / 'sub' / 'img1.jpg').write_bytes(b'C' * 100)
        (self.root / 'notes.txt').write_text('not a photo')
        data, evidence = self.run_tool(
            'organize_photos', {'folder': 'Santosh_Photos'})
        self.assertEqual(
            (data['copied_count'], data['duplicates_skipped'], data['found']),
            (3, 1, 4))
        target = self.root / 'Santosh_Photos'
        self.assertEqual((target / 'img1.jpg').read_bytes(), b'A' * 100)
        self.assertEqual((target / 'img2.png').read_bytes(), b'B' * 100)
        self.assertEqual((target / 'img1_2.jpg').read_bytes(), b'C' * 100)
        self.assertEqual(evidence['count'], 3)
        # Originals untouched, non-photos ignored.
        self.assertEqual((self.root / 'img1.jpg').read_bytes(), b'A' * 100)
        self.assertEqual((self.root / 'sub' / 'dup.jpg').read_bytes(), b'A' * 100)
        self.assertFalse((target / 'notes.txt').exists())
        # Re-run is stable: everything dedupes, nothing re-copies.
        rerun, _ = self.run_tool(
            'organize_photos', {'folder': 'Santosh_Photos'})
        self.assertEqual(
            (rerun['copied_count'], rerun['duplicates_skipped']), (0, 4))
        self.assertEqual(sorted(p.name for p in target.iterdir()),
                         ['img1.jpg', 'img1_2.jpg', 'img2.png'])

    def test_open_document_unique_match_only(self):
        (self.root / 'Quarterly Report.docx').write_bytes(b'doc')
        (self.root / 'notes.txt').write_text('hi')
        (self.root / 'sub' / 'photo.jpg').write_bytes(b'img')
        opened = []
        ctx = dict(self.ctx, open_file=opened.append)
        expected = str((self.root / 'Quarterly Report.docx').resolve())
        data, _ = handlers.dispatch(
            'open_document',
            TOOL_REGISTRY.validate('open_document', {'query': 'quarterly'}),
            ctx)
        self.assertEqual(opened, [expected])
        self.assertEqual(data['name'], 'Quarterly Report.docx')
        opened.clear()
        handlers.dispatch(
            'open_document',
            TOOL_REGISTRY.validate('open_document', {'query': 'a word document'}),
            ctx)
        self.assertEqual(opened, [expected])
        (self.root / 'sub' / 'Other.docx').write_bytes(b'doc2')
        for query in ('a word document', 'missing thing'):
            with self.assertRaises(NativeError) as error:
                handlers.dispatch(
                    'open_document',
                    TOOL_REGISTRY.validate('open_document', {'query': query}),
                    ctx)
            self.assertEqual(error.exception.code, 'no_match')
        self.assertEqual(len(opened), 1)

    def test_organize_photos_refuses_bad_folders(self):
        from tools import ToolError
        (self.root / 'blocker.txt').write_text('x')
        for bad in ('../out', 'sub/dir', '.hidden'):
            with self.assertRaises(ToolError):
                self.run_tool('organize_photos', {'folder': bad})

    def test_bounded_json_always_fits_and_parses(self):
        big = {'text': 'z' * 5000, 'items': [{'n': i} for i in range(100)]}
        raw = handlers.bounded_json(big)
        self.assertLessEqual(len(raw), 2000)
        self.assertTrue(json.loads(raw)['truncated'])
        small = {'ok': True}
        self.assertEqual(json.loads(handlers.bounded_json(small)), small)


if __name__ == '__main__':
    unittest.main()
