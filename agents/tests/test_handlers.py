import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import handlers  # noqa: E402
from native_search import NativeError, candidate_id_for  # noqa: E402
from tools import TOOL_REGISTRY, ToolError  # noqa: E402


def _one_page_pdf(line):
    """Minimal one-page text PDF with a correct xref table (no fixtures)."""
    content = b'BT /F1 12 Tf 10 100 Td (' + line + b') Tj ET'
    objects = [
        b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n',
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n',
        b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R'
        b'/Resources<</Font<</F1 5 0 R>>>>>>endobj\n',
        b'4 0 obj<</Length ' + str(len(content)).encode() + b'>>stream\n'
        + content + b'\nendstream\nendobj\n',
        b'5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n',
    ]
    out, offsets = b'%PDF-1.4\n', []
    for obj in objects:
        offsets.append(len(out))
        out += obj
    xref_at = len(out)
    out += ('xref\n0 6\n0000000000 65535 f \n' + ''.join(
        f'{off:010} 00000 n \n' for off in offsets
    ) + f'trailer<</Size 6/Root 1 0 R>>\nstartxref\n{xref_at}\n%%EOF\n').encode()
    return out


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

    def test_delete_trash_restore_round_trip(self):
        (self.root / 'old.txt').write_text('bye')
        ctx = dict(self.ctx, grants=[{**self.ctx['grants'][0], 'access': 'delete'}])
        data, _ = handlers.dispatch(
            'delete_files',
            TOOL_REGISTRY.validate('delete_files', {'path': 'old.txt', 'confirm': 'DELETE'}),
            ctx)
        self.assertEqual(data['trashed'], ['old.txt'])
        self.assertFalse((self.root / 'old.txt').exists())
        trash = list((self.root / '.pico-trash').glob('*old.txt'))
        self.assertEqual(len(trash), 1)
        self.assertEqual(trash[0].read_text(), 'bye')
        data, _ = handlers.dispatch(
            'restore_deleted', TOOL_REGISTRY.validate('restore_deleted', {'name': 'old.txt'}),
            ctx)
        self.assertEqual(data['restored'], 'old.txt')
        self.assertEqual((self.root / 'old.txt').read_text(), 'bye')

    def test_delete_needs_grant_and_confirm(self):
        from tools import ToolError
        (self.root / 'keep.txt').write_text('x')
        with self.assertRaises(ToolError):
            self.run_tool('delete_files', {'path': 'keep.txt', 'confirm': 'yes'})
        ctx = dict(self.ctx, grants=[{**self.ctx['grants'][0], 'access': 'delete'}])
        with self.assertRaises(ToolError):
            handlers.dispatch(
                'delete_files',
                TOOL_REGISTRY.validate('delete_files', {'path': 'keep.txt', 'confirm': 'yes'}),
                ctx)
        with self.assertRaises(NativeError) as denied:
            self.run_tool('delete_files', {'path': 'keep.txt', 'confirm': 'DELETE'})
        self.assertEqual(denied.exception.code, 'permission_denied')
        self.assertTrue((self.root / 'keep.txt').exists())
        with self.assertRaises(NativeError):
            handlers.dispatch(
                'restore_deleted', TOOL_REGISTRY.validate('restore_deleted', {'name': 'nope.txt'}),
                ctx)

    def test_convert_file_real_matrix(self):
        from PIL import Image
        Image.new('RGB', (8, 8), (200, 30, 30)).save(self.root / 'pic.jpg')
        Image.new('RGB', (8, 8), (30, 200, 30)).save(self.root / 'pic.png')
        data, _ = self.run_tool('convert_file', {'path': 'pic.jpg', 'to': 'pdf'})
        out = (self.root / data['path']).read_bytes()
        self.assertTrue(out.startswith(b'%PDF'))
        self.assertEqual(data['path'], 'pic.pdf')
        data, _ = self.run_tool('convert_file', {'path': 'pic.png', 'to': 'jpg'})
        self.assertTrue((self.root / data['path']).read_bytes().startswith(b'\xff\xd8'))
        (self.root / 'note.pdf').write_bytes(_one_page_pdf(b'Hello Pico'))
        data, _ = self.run_tool('convert_file', {'path': 'note.pdf', 'to': 'txt'})
        self.assertIn('Hello Pico', (self.root / data['path']).read_text())
        data, _ = self.run_tool('convert_file', {'path': 'note.pdf', 'to': 'docx'})
        from docx import Document
        text = '\n'.join(p.text for p in Document(self.root / data['path']).paragraphs)
        self.assertIn('Hello Pico', text)

    def test_convert_file_refusals_and_missing_engines(self):
        import sys
        from unittest import mock
        from tools import ToolError
        (self.root / 'a.txt').write_text('x')
        for args in ({'path': 'a.txt', 'to': 'pdf'},
                     {'path': 'missing.jpg', 'to': 'pdf'}):
            with self.assertRaises((ToolError, NativeError)):
                self.run_tool('convert_file', args)
        (self.root / 'b.png').write_bytes(b'not-an-image')
        with self.assertRaises(ToolError):
            self.run_tool('convert_file', {'path': 'b.png', 'to': 'jpg'})
        from PIL import Image
        Image.new('RGB', (4, 4)).save(self.root / 'c.jpg')
        with self.assertRaises(ToolError) as same:
            self.run_tool('convert_file', {'path': 'c.jpg', 'to': 'jpg'})
        self.assertIn('already', str(same.exception))
        with mock.patch.dict(sys.modules, {'PIL': None, 'PIL.Image': None}):
            with self.assertRaises(ToolError) as missing:
                self.run_tool('convert_file', {'path': 'c.jpg', 'to': 'png'})
        self.assertIn('pip install pillow', str(missing.exception))
        (self.root / 'd.docx').write_bytes(b'fake-docx')
        with mock.patch('shutil.which', return_value=None):
            with self.assertRaises(ToolError) as office:
                self.run_tool('convert_file', {'path': 'd.docx', 'to': 'pdf'})
        self.assertIn('LibreOffice', str(office.exception))

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

    def test_open_app_resolves_new_allowlisted_apps(self):
        data, _ = self.run_tool('open_app', {'app': 'chrome'})
        self.assertEqual(data, {'app': 'chrome'})
        data, _ = self.run_tool('open_app', {'app': 'files'})
        self.assertEqual(data, {'app': 'files'})
        self.assertEqual(self.calls, [('reopen', 'com.google.Chrome'),
                                      ('reopen', 'com.apple.finder')])

    def _write_pdf(self, name, pages, password=None):
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(72, 72)
        if password:
            writer.encrypt(password)
        path = self.root / name
        with path.open('wb') as stream:
            writer.write(stream)
        return path

    def _pdf_page_count(self, path):
        from pypdf import PdfReader
        with path.open('rb') as stream:
            return len(PdfReader(stream).pages)

    def _pdf_pages(self, **args):
        import json as _json
        call = {'action': args.pop('action'), 'paths_json': _json.dumps(args.pop('paths'))}
        call.update(args)
        return self.run_tool('pdf_pages', call)

    def test_pdf_pages_merge_split_rotate_delete(self):
        self._write_pdf('a.pdf', 2)
        self._write_pdf('b.pdf', 1)
        data, _ = self._pdf_pages(action='merge', paths=['a.pdf', 'b.pdf'])
        self.assertEqual(self._pdf_page_count(self.root / data['output']), 3)
        data, _ = self._pdf_pages(action='split', paths=['a.pdf'], pages='1-2')
        self.assertEqual(self._pdf_page_count(self.root / data['output']), 2)
        data, _ = self._pdf_pages(action='rotate', paths=['b.pdf'], angle='90')
        from pypdf import PdfReader
        with (self.root / data['output']).open('rb') as stream:
            self.assertEqual(PdfReader(stream).pages[0].get('/Rotate'), 90)
        data, _ = self._pdf_pages(action='delete', paths=['a.pdf'], pages='1')
        self.assertEqual(self._pdf_page_count(self.root / data['output']), 1)
        self.assertEqual(self._pdf_page_count(self.root / 'a.pdf'), 2)

    def test_pdf_pages_watermark_unlock_and_images(self):
        from unittest import mock
        self._write_pdf('r.pdf', 2)
        before = (self.root / 'r.pdf').stat().st_size
        data, _ = self._pdf_pages(action='watermark', paths=['r.pdf'], text='DRAFT')
        out = self.root / data['output']
        self.assertEqual(self._pdf_page_count(out), 2)
        self.assertGreater(out.stat().st_size, before)
        self._write_pdf('s.pdf', 1, password='rosebud')
        data, _ = self._pdf_pages(action='unlock', paths=['s.pdf'], password='rosebud')
        self.assertEqual(self._pdf_page_count(self.root / data['output']), 1)
        with self.assertRaises(ToolError) as wrong:
            self._pdf_pages(action='unlock', paths=['s.pdf'], password='nope')
        self.assertIn('password', str(wrong.exception).lower())
        with mock.patch('shutil.which', return_value=None):
            with self.assertRaises(ToolError) as missing:
                self._pdf_pages(action='images', paths=['r.pdf'])
        self.assertIn('poppler', str(missing.exception).lower())

    def test_pdf_pages_refusals(self):
        self._write_pdf('a.pdf', 2)
        bad = [
            {'action': 'merge', 'paths': ['a.pdf']},
            {'action': 'split', 'paths': ['a.pdf'], 'pages': '9-10'},
            {'action': 'split', 'paths': ['a.pdf'], 'pages': 'soon'},
            {'action': 'rotate', 'paths': ['a.pdf'], 'angle': '45'},
            {'action': 'watermark', 'paths': ['a.pdf'], 'text': '  '},
            {'action': 'unlock', 'paths': ['a.pdf']},
            {'action': 'merge', 'paths': ['a.pdf', 'missing.pdf']},
        ]
        for args in bad:
            with self.assertRaises((NativeError, ToolError), msg=args):
                self._pdf_pages(**args)

    def test_open_document_asks_which_on_many_matches(self):
        (self.root / 'Report A.pdf').write_bytes(b'a')
        (self.root / 'Report B.pdf').write_bytes(b'b')
        with self.assertRaises(NativeError) as error:
            self.run_tool('open_document', {'query': 'report'})
        self.assertEqual(error.exception.code, 'no_match')
        self.assertIn('Which one', str(error.exception))
        self.assertIn('Report A.pdf', str(error.exception))

    def test_open_document_opens_a_folder_by_name(self):
        (self.root / 'Trip Photos').mkdir()
        (self.root / 'Trip Photos' / 'a.jpg').write_bytes(b'img')
        opened = []
        ctx = dict(self.ctx, open_file=opened.append)
        data, _ = handlers.dispatch(
            'open_document',
            TOOL_REGISTRY.validate('open_document', {'query': 'trip photos folder'}),
            ctx)
        self.assertEqual(opened, [str((self.root / 'Trip Photos').resolve())])
        self.assertEqual(data['name'], 'Trip Photos')

    def test_open_document_opens_pdf_and_any_file_type(self):
        (self.root / 'Syllabus.pdf').write_bytes(b'%PDF-1.4 fake')
        (self.root / 'lecture.mp4').write_bytes(b'video')
        (self.root / 'backup.zip').write_bytes(b'zip')
        opened = []
        ctx = dict(self.ctx, open_file=opened.append, connected=True)
        for name, query in (('Syllabus.pdf', 'syllabus'),
                            ('lecture.mp4', 'lecture'),
                            ('backup.zip', 'backup')):
            opened.clear()
            data, _ = handlers.dispatch(
                'open_document',
                TOOL_REGISTRY.validate('open_document', {'query': query}),
                ctx)
            self.assertEqual(opened, [str((self.root / name).resolve())])
            self.assertEqual(data['name'], name)
        opened.clear()
        handlers.dispatch(
            'open_document',
            TOOL_REGISTRY.validate('open_document', {'query': 'a video'}),
            ctx)
        self.assertEqual(opened, [str((self.root / 'lecture.mp4').resolve())])

    def test_organize_photos_scans_every_granted_root(self):
        import tempfile as _tempfile
        other = _tempfile.TemporaryDirectory(prefix='pico-handlers-2-')
        self.addCleanup(other.cleanup)
        second = Path(other.name)
        (self.root / 'a.jpg').write_bytes(b'A' * 40)
        (second / 'b.png').write_bytes(b'B' * 40)
        ctx = dict(self.ctx, grants=[
            {**self.ctx['grants'][0], 'access': 'write'},
            {'path': str(second), 'access': 'read', 'id': 'g2',
             'granted_at': 't', 'source': 'test'}])
        data, _ = handlers.dispatch(
            'organize_photos',
            TOOL_REGISTRY.validate('organize_photos', {'folder': 'All'}),
            ctx)
        self.assertEqual((data['copied_count'], data['found']), (2, 2))
        target = self.root / 'All'
        self.assertTrue((target / 'a.jpg').exists())
        self.assertTrue((target / 'b.png').exists())

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

    def test_rename_file_round_trip(self):
        (self.root / 'old.txt').write_text('keep me')
        (self.root / 'taken.txt').write_text('taken')
        data, evidence = self.run_tool(
            'rename_file', {'path': 'old.txt', 'new_name': 'new.txt'})
        self.assertEqual(data['path'], 'new.txt')
        self.assertEqual(data['previous'], 'old.txt')
        self.assertEqual(evidence['digest'], data['digest'])
        self.assertEqual((self.root / 'new.txt').read_text(), 'keep me')
        self.assertFalse((self.root / 'old.txt').exists())
        with self.assertRaises(NativeError) as missing:
            self.run_tool('rename_file', {'path': 'gone.txt', 'new_name': 'x.txt'})
        self.assertEqual(missing.exception.code, 'no_match')
        for bad in ('taken.txt', '../out.txt', '.hidden', 'a/b.txt'):
            with self.assertRaises(ToolError, msg=bad):
                self.run_tool('rename_file', {'path': 'new.txt', 'new_name': bad})
        self.assertEqual((self.root / 'new.txt').read_text(), 'keep me')
        (self.root / 'sub').mkdir(exist_ok=True)
        with self.assertRaises(ToolError):
            self.run_tool('rename_file', {'path': 'sub', 'new_name': 'sub2'})

    def test_duplicate_file_numbered_copy(self):
        (self.root / 'pic.bin').write_bytes(b'\x00\x01pic')
        first, _ = self.run_tool('duplicate_file', {'path': 'pic.bin'})
        self.assertEqual(first['path'], 'pic_copy.bin')
        self.assertEqual(first['source'], 'pic.bin')
        self.assertEqual((self.root / 'pic_copy.bin').read_bytes(), b'\x00\x01pic')
        second, _ = self.run_tool('duplicate_file', {'path': 'pic.bin'})
        self.assertEqual(second['path'], 'pic_copy_2.bin')
        self.assertEqual((self.root / 'pic.bin').read_bytes(), b'\x00\x01pic')
        with self.assertRaises(NativeError):
            self.run_tool('duplicate_file', {'path': 'missing.bin'})

    def test_archive_create_and_extract(self):
        import io
        import zipfile
        (self.root / 'a.txt').write_text('aaa')
        (self.root / 'docs').mkdir()
        (self.root / 'docs' / 'b.txt').write_text('bbb')
        data, _ = self.run_tool('archive', {
            'action': 'create',
            'paths_json': json.dumps(['a.txt', 'docs']),
            'output': 'bundle.zip'})
        out = self.root / data['path']
        self.assertTrue(out.read_bytes().startswith(b'PK'))
        self.assertEqual(data['count'], 2)
        data, _ = self.run_tool('archive', {
            'action': 'extract', 'paths_json': json.dumps(['bundle.zip']),
            'output': 'restored'})
        self.assertEqual(data['output'], 'restored')
        self.assertEqual((self.root / 'restored' / 'a.txt').read_text(), 'aaa')
        self.assertEqual(
            (self.root / 'restored' / 'docs' / 'b.txt').read_text(), 'bbb')
        evil = io.BytesIO()
        with zipfile.ZipFile(evil, 'w') as zf:
            zf.writestr('../evil.txt', 'escape')
        (self.root / 'evil.zip').write_bytes(evil.getvalue())
        with self.assertRaises(ToolError) as slip:
            self.run_tool('archive', {
                'action': 'extract', 'paths_json': json.dumps(['evil.zip'])})
        self.assertIn('escape', str(slip.exception))
        self.assertFalse((self.root.parent / 'evil.txt').exists())
        with self.assertRaises(ToolError):
            self.run_tool('archive', {
                'action': 'create', 'paths_json': json.dumps(['missing.txt'])})
        self.assertFalse((self.root / 'evil').exists())

    def test_recent_files_lists_newest(self):
        import os as _os
        import time
        ancient = time.time() - 30 * 86400
        for child in self.root.iterdir():
            if child.is_file():
                _os.utime(child, (ancient, ancient))
        (self.root / 'fresh.txt').write_text('fresh')
        data, _ = self.run_tool('recent_files', {'days': '7'})
        self.assertEqual([f['name'] for f in data['files']], ['fresh.txt'])
        self.assertIn('candidate_id', data['files'][0])
        self.assertIn('modified', data['files'][0])
        data, _ = self.run_tool('recent_files', {'days': '60'})
        names = [f['name'] for f in data['files']]
        self.assertEqual(names[0], 'fresh.txt')
        self.assertIn('brief.txt', names)
        self.assertFalse(data['truncated'])
        quiet = self.root / 'quiet'
        quiet.mkdir()
        (quiet / 'old.txt').write_text('old')
        _os.utime(quiet / 'old.txt', (ancient, ancient))
        ctx = dict(self.ctx, grants=[{**self.ctx['grants'][0],
                                     'path': str(quiet)}])
        empty, _ = handlers.dispatch(
            'recent_files',
            TOOL_REGISTRY.validate('recent_files', {'days': '7'}), ctx)
        self.assertEqual(empty['files'], [])
        self.assertEqual(empty['found'], 0)

    def test_search_contents_finds_snippets(self):
        (self.root / 'budget.txt').write_text('line one\nlaunch budget 2025\nlast\n')
        (self.root / 'notes.txt').write_text('groceries and milk')
        (self.root / 'binary.bin').write_bytes(b'\x00\x01budget\xff')
        data, _ = self.run_tool('search_contents', {'query': 'BUDGET'})
        self.assertEqual([m['name'] for m in data['matches']], ['budget.txt'])
        self.assertEqual(data['matches'][0]['line'], 2)
        self.assertIn('budget', data['matches'][0]['excerpt'])
        self.assertIn('candidate_id', data['matches'][0])
        missing, _ = self.run_tool('search_contents', {'query': 'zzzz-nope'})
        self.assertEqual(missing['matches'], [])
        self.assertEqual(missing['found'], 0)

    def test_find_duplicates_groups_copies(self):
        (self.root / 'a.txt').write_bytes(b'same-bytes-here')
        (self.root / 'sub' / 'b.txt').write_bytes(b'same-bytes-here')
        (self.root / 'c.txt').write_bytes(b'lonely')
        (self.root / 'empty1.txt').write_bytes(b'')
        (self.root / 'empty2.txt').write_bytes(b'')
        data, _ = self.run_tool('find_duplicates', {})
        self.assertEqual(data['found'], 1)
        group = data['groups'][0]
        self.assertEqual(group['count'], 2)
        self.assertEqual({f['name'] for f in group['files']}, {'a.txt', 'b.txt'})
        self.assertTrue(all('candidate_id' in f for f in group['files']))
        (self.root / 'sub' / 'b.txt').unlink()
        (self.root / 'a.txt').unlink()
        again, _ = self.run_tool('find_duplicates', {})
        self.assertEqual(again['groups'], [])

    def test_largest_files_orders_by_size(self):
        (self.root / 'tiny.txt').write_bytes(b'x' * 10)
        (self.root / 'mid.txt').write_bytes(b'x' * 100)
        (self.root / 'big.bin').write_bytes(b'x' * 1000)
        data, _ = self.run_tool('largest_files', {})
        names = [f['name'] for f in data['files']]
        self.assertLess(names.index('big.bin'), names.index('mid.txt'))
        self.assertLess(names.index('mid.txt'), names.index('tiny.txt'))
        self.assertEqual(data['limit'], 10)
        capped, _ = self.run_tool('largest_files', {'limit': '2'})
        self.assertEqual(len(capped['files']), 2)
        self.assertEqual(capped['files'][0]['name'], 'big.bin')

    def test_undo_edit_restores_and_trashes_create(self):
        created, _ = self.run_tool('fs_write', {'path': 'note.txt', 'content': 'v1'})
        self.run_tool('fs_write', {'path': 'note.txt', 'content': 'v2',
                                   'base_revision': created['digest']})
        undone, _ = self.run_tool('undo_edit', {'path': 'note.txt'})
        self.assertEqual(undone['undone'], 'revise')
        self.assertEqual((self.root / 'note.txt').read_text(), 'v1')
        removed, _ = self.run_tool('undo_edit', {'path': 'note.txt'})
        self.assertEqual(removed['undone'], 'create')
        self.assertFalse((self.root / 'note.txt').exists())
        trashed = list((self.root / '.pico-trash').glob('*note.txt'))
        self.assertEqual(len(trashed), 1)
        with self.assertRaises(NativeError) as consumed:
            self.run_tool('undo_edit', {'path': 'note.txt'})
        self.assertEqual(consumed.exception.code, 'no_match')
        self.run_tool('fs_write', {'path': 'other.txt', 'content': 'pico'})
        (self.root / 'other.txt').write_text('hand-edited')
        with self.assertRaises(NativeError) as changed:
            self.run_tool('undo_edit', {'path': 'other.txt'})
        self.assertEqual(changed.exception.code, 'candidate_changed')
        self.assertEqual((self.root / 'other.txt').read_text(), 'hand-edited')
        with self.assertRaises(NativeError):
            self.run_tool('undo_edit', {'path': 'missing.txt'})

    def test_empty_trash_needs_confirm_and_delete_rank(self):
        ctx = dict(self.ctx, grants=[{**self.ctx['grants'][0], 'access': 'delete'}])
        (self.root / 'old.txt').write_text('bye')
        handlers.dispatch(
            'delete_files',
            TOOL_REGISTRY.validate('delete_files', {'path': 'old.txt', 'confirm': 'DELETE'}),
            ctx)
        trash_files = list((self.root / '.pico-trash').iterdir())
        self.assertEqual(len(trash_files), 2)
        with self.assertRaises(ToolError):
            handlers.dispatch(
                'empty_trash',
                TOOL_REGISTRY.validate('empty_trash', {'confirm': 'yes'}), ctx)
        self.assertEqual(len(list((self.root / '.pico-trash').iterdir())), 2)
        data, _ = handlers.dispatch(
            'empty_trash',
            TOOL_REGISTRY.validate('empty_trash', {'confirm': 'EMPTY'}), ctx)
        self.assertEqual(data['emptied_count'], 1)
        self.assertGreater(data['freed_bytes'], 0)
        self.assertEqual(list((self.root / '.pico-trash').iterdir()), [])
        with self.assertRaises(NativeError) as denied:
            self.run_tool('empty_trash', {'confirm': 'EMPTY'})
        self.assertEqual(denied.exception.code, 'permission_denied')
        again, _ = handlers.dispatch(
            'empty_trash',
            TOOL_REGISTRY.validate('empty_trash', {'confirm': 'EMPTY'}), ctx)
        self.assertEqual(again['emptied_count'], 0)

    def test_archive_outputs_are_undoable(self):
        (self.root / 'a.txt').write_text('aaa')
        created, _ = self.run_tool('archive', {
            'action': 'create', 'paths_json': json.dumps(['a.txt']),
            'output': 'bundle.zip'})
        self.assertTrue((self.root / 'bundle.zip').exists())
        self.run_tool('archive', {
            'action': 'extract', 'paths_json': json.dumps(['bundle.zip']),
            'output': 'restored'})
        self.assertEqual((self.root / 'restored' / 'a.txt').read_text(), 'aaa')
        undone, _ = self.run_tool('undo_edit', {'path': 'restored/a.txt'})
        self.assertEqual(undone['undone'], 'create')
        self.assertFalse((self.root / 'restored' / 'a.txt').exists())
        undone, _ = self.run_tool('undo_edit', {'path': 'bundle.zip'})
        self.assertEqual(undone['undone'], 'create')
        self.assertFalse((self.root / 'bundle.zip').exists())
        self.assertEqual(created['path'], 'bundle.zip')

    def test_disk_usage_reports_totals(self):
        (self.root / 'a.txt').write_bytes(b'x' * 100)
        (self.root / 'sub' / 'b.txt').write_bytes(b'y' * 300)
        data, _ = self.run_tool('disk_usage', {})
        self.assertEqual(data['total_bytes'], 411)
        self.assertEqual(data['file_count'], 3)
        self.assertEqual(data['roots'][0]['name'], self.root.name)
        folders = {f['path']: f['size_bytes'] for f in data['largest_folders']}
        self.assertGreaterEqual(folders[f'{self.root.name}/sub'], 300)
        self.assertFalse(data['truncated'])


if __name__ == '__main__':
    unittest.main()
