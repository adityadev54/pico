"""Remote tool path end to end (A06/A07): relay mail protocol on one side,
real helper execution on a fixture workspace on the other. The only fakes
are the Supabase transport and the tkinter shell around execute_tool.
"""
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'agents'))

import handlers  # noqa: E402
from relay.service import PicoService  # noqa: E402
from relay.state import RelayState  # noqa: E402
from relay.tests.fake import FakeSupabase  # noqa: E402
from tools import TOOL_REGISTRY  # noqa: E402


class ToolPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-toolpath-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'project').mkdir()
        self.db = FakeSupabase()
        self.service = PicoService(self.db, RelayState(self.root / 's.sqlite'))
        self.owner = 'owner-1'
        self.device = {'id': str(uuid.uuid4()), 'user_id': self.owner,
                       'name': 'Pico · Test', 'os': 'macos', 'revoked_at': None}
        self.db.tables['devices'].append(dict(self.device))
        self.ctx = {'task_id': '', 'grants': [
            {'path': str(self.root / 'project'), 'access': 'write'}],
                    'transfer': lambda r, e: None, 'open_url': lambda u: None,
                    'reopen': lambda b: None, 'notify': lambda: None}

    def seed_task(self, kind):
        rows = self.db.db('tasks', body={
            'user_id': self.owner, 'device_id': self.device['id'], 'kind': kind,
            'input': {}, 'status': 'queued'}, method='POST')
        return rows[0]

    def helper_turn(self, mail):
        """What companion.execute_tool does, minus tkinter: validate, run,
        return the tool_result payload it would queue."""
        payload = mail['payload']
        args = TOOL_REGISTRY.validate(payload['tool'], payload)
        data, evidence = handlers.dispatch(payload['tool'], args, self.ctx)
        return {'task_id': payload['task_id'], 'call_id': payload['call_id'],
                'status': 'succeeded', 'data_json': handlers.bounded_json(data),
                'evidence_json': handlers.bounded_json(evidence)}

    def test_fs_write_read_round_trip_over_mail(self):
        task = self.seed_task('fs_write')
        call_id = str(uuid.uuid4())
        self.service.enqueue(self.owner, self.device['id'], 'tool_call', {
            'task_id': task['id'], 'tool': 'fs_write', 'call_id': call_id,
            'path': 'hello.txt', 'content': 'actual bytes here'}, call_id)
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertEqual((self.root / 'project' / 'hello.txt').read_text(),
                         'actual bytes here')

        read_task = self.seed_task('fs_read')
        read_call = str(uuid.uuid4())
        self.service.enqueue(self.owner, self.device['id'], 'tool_call', {
            'task_id': read_task['id'], 'tool': 'fs_read', 'call_id': read_call,
            'path': 'hello.txt'}, read_call)
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['payload'].get('call_id') == read_call][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + read_task['id']})[0]
        self.assertEqual(row['result']['content'], 'actual bytes here')

    def test_stale_revision_fails_cleanly_over_mail(self):
        (self.root / 'project' / 'note.txt').write_text('v1')
        task = self.seed_task('fs_write')
        call_id = str(uuid.uuid4())
        self.service.enqueue(self.owner, self.device['id'], 'tool_call', {
            'task_id': task['id'], 'tool': 'fs_write', 'call_id': call_id,
            'path': 'note.txt', 'content': 'v2'}, call_id)
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['payload'].get('call_id') == call_id][0]
        from native_search import NativeError
        try:
            self.helper_turn(mail)
            self.fail('expected stale/create conflict')
        except NativeError as error:
            self.service.complete_tool_result(self.owner, self.device['id'], {
                'task_id': task['id'], 'status': 'failed', 'error_code': error.code})
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['result']['error_code'], 'candidate_changed')
        self.assertEqual((self.root / 'project' / 'note.txt').read_text(), 'v1')

    def test_create_note_over_mail_saves_real_file(self):
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'create_note',
            {'name': 'meeting-notes.txt', 'text': 'actual bytes here'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.assertEqual(mail['payload']['path'], 'meeting-notes.txt')
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertEqual((self.root / 'project' / 'meeting-notes.txt').read_text(),
                         'actual bytes here')
        self.assertTrue(row['result']['digest'])

    def test_steer_renames_target_before_the_write(self):
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'create_note',
            {'name': 'draft.txt', 'text': 'v1'})
        receipt = self.service.steer_task(self.owner, task['id'], 'final.txt')
        self.assertTrue(receipt['steered'])
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.assertEqual(mail['payload']['path'], 'final.txt')
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        self.assertFalse((self.root / 'project' / 'draft.txt').exists())
        self.assertEqual((self.root / 'project' / 'final.txt').read_text(), 'v1')
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('renamed to final.txt', row['result']['message'])

    def test_phone_upload_lands_exact_bytes_in_workspace(self):
        import base64
        raw = b'\xff\xd8\xff' + bytes(range(256)) * 100
        out = self.service.upload_artifact(
            self.owner, self.device['id'], '', 'photo.jpg',
            base64.b64encode(raw).decode(), 'transfer')
        self.assertFalse(out['duplicate'])
        self.ctx['fetch_artifact'] = lambda aid: base64.b64decode(
            self.service.artifact_for_helper(
                self.owner, self.device['id'], aid)['content_base64'])
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.assertEqual(mail['payload']['tool'], 'fetch_upload')
        self.assertEqual(mail['payload']['artifact_id'], out['artifact_id'])
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + out['task_id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertEqual((self.root / 'project' / 'photo.jpg').read_bytes(), raw)
        self.assertEqual(row['result']['digest'], out['artifact_id'])
        resumed = self.service.upload_artifact(
            self.owner, self.device['id'], '', 'photo.jpg',
            base64.b64encode(raw).decode(), 'transfer')
        self.assertTrue(resumed['duplicate'])
        mail2 = [m for m in self.service.mailbox(self.owner, self.device['id'])
                 if m['payload'].get('task_id') == resumed['task_id']][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail2))
        row2 = self.db.db('tasks', {'id': 'eq.' + resumed['task_id']})[0]
        self.assertEqual(row2['status'], 'completed')
        self.assertTrue(row2['result']['duplicate'])
        self.assertEqual((self.root / 'project' / 'photo.jpg').read_bytes(), raw)

    def test_delete_over_mail_trashes_and_restores(self):
        (self.root / 'project' / 'old.txt').write_text('bye')
        self.ctx['grants'] = [{'path': str(self.root / 'project'), 'access': 'delete',
                               'id': 'g', 'granted_at': 't', 'source': 'test'}]
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'delete_files',
            {'path': 'old.txt', 'confirm': 'DELETE'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertFalse((self.root / 'project' / 'old.txt').exists())
        self.assertTrue((self.root / 'project' / '.pico-trash').is_dir())
        back = self.service.create_task(
            self.owner, self.device['id'], '', 'restore_deleted', {'name': 'old.txt'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['payload'].get('task_id') == back['id']][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + back['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertEqual((self.root / 'project' / 'old.txt').read_text(), 'bye')

    def test_convert_file_over_mail(self):
        from PIL import Image
        Image.new('RGB', (8, 8), (10, 10, 200)).save(self.root / 'project' / 'pic.png')
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'convert_file',
            {'path': 'pic.png', 'to': 'jpg'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertTrue((self.root / 'project' / 'pic.jpg').read_bytes().startswith(b'\xff\xd8'))
        self.assertIn('Converted to pic.jpg', row['result']['message'])

    def test_open_document_over_mail(self):
        (self.root / 'project' / 'Quarterly Report.docx').write_bytes(b'doc')
        opened = []
        self.ctx['open_file'] = opened.append
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'open_document',
            {'query': 'quarterly'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        self.assertEqual(opened, [str((self.root / 'project' / 'Quarterly Report.docx').resolve())])
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('Opened Quarterly Report.docx', row['result']['message'])

    def test_rename_round_trip_over_mail(self):
        (self.root / 'project' / 'old.txt').write_text('keep')
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'rename_file',
            {'path': 'old.txt', 'new_name': 'new.txt'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        self.assertEqual((self.root / 'project' / 'new.txt').read_text(), 'keep')
        self.assertFalse((self.root / 'project' / 'old.txt').exists())
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('Renamed old.txt to new.txt', row['result']['message'])

    def test_search_contents_round_trip_over_mail(self):
        (self.root / 'project' / 'budget.txt').write_text('launch budget 2025')
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'search_contents',
            {'query': 'budget'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('1 file(s) contain that text', row['result']['message'])
        self.assertIn('budget.txt', row['result']['message'])

    def test_undo_edit_round_trip_over_mail(self):
        import hashlib as _hashlib
        (self.root / 'project' / 'note.txt').write_text('v1')
        handlers.dispatch(
            'fs_write',
            TOOL_REGISTRY.validate('fs_write', {
                'path': 'note.txt', 'content': 'v2',
                'base_revision': _hashlib.sha256(b'v1').hexdigest()}),
            self.ctx)
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'undo_edit',
            {'path': 'note.txt'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        self.assertEqual((self.root / 'project' / 'note.txt').read_text(), 'v1')
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('Restored the previous version of note.txt',
                      row['result']['message'])

    def test_reviewed_create_stamps_phone_approval(self):
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'open_website',
            {'url': 'https://example.com/x'})
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertIs(row['input'].get('_pico_phone_approved'), True)
        plain = self.service.create_task(
            self.owner, self.device['id'], '', 'find_document',
            {'query': 'brief'})
        row = self.db.db('tasks', {'id': 'eq.' + plain['id']})[0]
        self.assertNotIn('_pico_phone_approved', row['input'])

    def test_pdf_pages_merge_over_mail(self):
        from pypdf import PdfWriter
        for name in ('a.pdf', 'b.pdf'):
            writer = PdfWriter()
            writer.add_blank_page(72, 72)
            with (self.root / 'project' / name).open('wb') as stream:
                writer.write(stream)
        import json as _json
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'pdf_pages',
            {'action': 'merge',
             'paths_json': _json.dumps(['a.pdf', 'b.pdf'])})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertTrue(row['input'].get('_pico_phone_approved') is True)

    def test_pdf_pages_prepare_refusals(self):
        from relay.service import ApiError
        bad = [
            {'action': 'merge', 'paths_json': '["a.pdf"]'},
            {'action': 'split', 'paths_json': '["a.pdf"]', 'pages': 'soon'},
            {'action': 'rotate', 'paths_json': '["a.pdf"]', 'angle': '45'},
            {'action': 'fly', 'paths_json': '["a.pdf"]'},
        ]
        for source in bad:
            with self.assertRaises(ApiError, msg=source):
                self.service.create_task(
                    self.owner, self.device['id'], '', 'pdf_pages', source)

    def test_organize_photos_over_mail(self):
        (self.root / 'project' / 'a.jpg').write_bytes(b'A' * 50)
        (self.root / 'project' / 'sub').mkdir()
        (self.root / 'project' / 'sub' / 'b.png').write_bytes(b'B' * 50)
        (self.root / 'project' / 'sub' / 'dup.jpg').write_bytes(b'A' * 50)
        task = self.service.create_task(
            self.owner, self.device['id'], '', 'organize_photos',
            {'folder': 'Santosh_Photos'})
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['kind'] == 'tool_call'][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        target = self.root / 'project' / 'Santosh_Photos'
        self.assertEqual(sorted(p.name for p in target.iterdir()),
                         ['a.jpg', 'b.png'])
        self.assertEqual((target / 'a.jpg').read_bytes(), b'A' * 50)
        self.assertIn('Gathered 2 photo(s)', row['result']['message'])
        self.assertIn('skipped 1 duplicate(s)', row['result']['message'])

    def test_process_run_over_mail(self):
        import sys as _sys
        task = self.seed_task('process_run')
        call_id = str(uuid.uuid4())
        self.service.enqueue(self.owner, self.device['id'], 'tool_call', {
            'task_id': task['id'], 'tool': 'process_run', 'call_id': call_id,
            'argv_json': json.dumps([_sys.executable, '-c', 'print(6 * 7)']),
            'timeout_s': '10'}, call_id)
        mail = [m for m in self.service.mailbox(self.owner, self.device['id'])
                if m['payload'].get('call_id') == call_id][0]
        self.service.complete_tool_result(
            self.owner, self.device['id'], self.helper_turn(mail))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertEqual(row['result']['stdout'], '42\n')


if __name__ == '__main__':
    unittest.main()
