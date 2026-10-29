import base64
import hashlib
import json
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from relay.app import access_line
from relay.service import ApiError, PicoService, digest, merge_upload_result
from relay.state import RelayState
from relay.tests.fake import FakeSupabase


def device_row(owner='owner-1'):
    return {'id': str(uuid.uuid4()), 'user_id': owner, 'name': 'Pico · Test Mac',
            'os': 'macos', 'revoked_at': None, 'helper_version': '0.3.0',
            'last_seen': datetime.now(timezone.utc).isoformat()}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-relay-service-')
        self.addCleanup(self.tmp.cleanup)
        self.db = FakeSupabase()
        self.service = PicoService(self.db, RelayState(Path(self.tmp.name) / 's.sqlite'))
        self.owner = 'owner-1'
        self.device = device_row()
        self.db.tables['devices'].append(dict(self.device))

    def test_user_needs_token(self):
        with self.assertRaises(ApiError) as ctx:
            self.service.user('')
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(self.service.user('anything'), 'owner-1')

    def test_unknown_device_token_rejected(self):
        with self.assertRaises(ApiError) as ctx:
            self.service.device('pico_unknown')
        self.assertEqual(ctx.exception.status, 401)

    def test_devices_falls_back_without_helper_version(self):
        self.db.helper_version_supported = False
        self.assertEqual(len(self.service.devices(self.owner)), 1)

    def test_pairing_then_second_pairing_conflicts(self):
        self.db.tables['devices'].clear()
        pairing = self.service.pairing(self.owner)
        self.assertRegex(pairing['code'], r'^\d{6}$')
        # Claiming tested below; a device blocks the next code.
        self.db.tables['devices'].append(device_row())
        with self.assertRaises(ApiError) as ctx:
            self.service.pairing(self.owner)
        self.assertEqual(ctx.exception.status, 409)

    def test_claim_reuse_and_lockout(self):
        self.db.tables['devices'].clear()
        self.db.tables['pairing_codes'].append({
            'code_hash': digest('pico:123456'), 'user_id': self.owner,
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            'claimed_at': None})
        claimed = self.service.claim({'code': '123456', 'os': 'macos', 'name': 'Mac'}, 'addr-9')
        self.assertTrue(claimed['token'].startswith('pico_'))
        resolved = self.service.device(claimed['token'])
        self.assertEqual(resolved['id'], claimed['device_id'])
        with self.assertRaises(ApiError):
            self.service.claim({'code': '123456', 'os': 'macos'}, 'addr-9')
        for _ in range(5):
            with self.assertRaises(ApiError):
                self.service.claim({'code': 'not-a-code', 'os': 'macos'}, 'addr-10')
        with self.assertRaises(ApiError) as ctx:
            self.service.claim({'code': '000000', 'os': 'macos'}, 'addr-10')
        self.assertEqual(ctx.exception.status, 429)

    def test_enqueue_rejects_snapshots_tools_and_oversize(self):
        bad = [
            {'snapshot': 'x'},
            {'task_id': 't', 'tool': 'wipe_disk'},
            {'sentence': 'x' * 2001},
            {'character': 'zed'},
            {'mood': 'dancing'},
            {'size': 'huge'},
        ]
        for payload in bad:
            kind = 'tool_call' if 'tool' in payload else 'place'
            with self.assertRaises(ApiError, msg=payload):
                self.service.enqueue(self.owner, self.device['id'], kind, payload)
        future = str(int(datetime.now(timezone.utc).timestamp() * 1000) + 120000)
        with self.assertRaises(ApiError):
            self.service.enqueue(self.owner, self.device['id'], 'companion',
                                 {'mood': 'idle', 'mood_until': future})

    def test_companion_dedupes_and_retry_is_single(self):
        self.service.enqueue(self.owner, self.device['id'], 'companion',
                             {'character': 'mica'})
        self.service.enqueue(self.owner, self.device['id'], 'companion',
                             {'character': 'tuck'})
        mail = self.service.mailbox(self.owner, self.device['id'])
        self.assertEqual([m['payload']['character'] for m in mail], ['tuck'])
        self.service.acknowledge(self.owner, self.device['id'], [m['id'] for m in mail])
        self.assertEqual(self.service.mailbox(self.owner, self.device['id']), [])
        pid = str(uuid.uuid4())
        self.service.enqueue(self.owner, self.device['id'], 'place',
                             {'place_id': pid, 'sentence': 'hi'}, pid)
        mail = self.service.mailbox(self.owner, self.device['id'])
        self.service.acknowledge(self.owner, self.device['id'], [m['id'] for m in mail])
        repeat = self.service.enqueue(self.owner, self.device['id'], 'place',
                                      {'place_id': pid, 'sentence': 'hi'}, pid)
        self.assertEqual(repeat['status'], 'delivered')

    def test_create_task_validates_kind_and_input(self):
        with self.assertRaises(ApiError):
            self.service.create_task(self.owner, self.device['id'], '', 'wipe_disk', {})
        with self.assertRaises(ApiError):
            self.service.create_task(self.owner, self.device['id'], '', 'find_document', {'query': '  '})
        with self.assertRaises(ApiError):
            self.service.create_task(self.owner, self.device['id'], '', 'send_file',
                                     {'candidate_id': 'c1'})
        with self.assertRaises(ApiError):
            self.service.create_task(self.owner, self.device['id'], '', 'open_website',
                                     {'url': 'ftp://x'})
        task = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                        {'query': 'brief'})
        self.assertEqual(task['status'], 'queued')
        calls = [m for m in self.service.mailbox(self.owner, self.device['id'])
                 if m['kind'] == 'tool_call']
        self.assertEqual(calls[0]['payload']['tool'], 'search_documents')
        self.assertEqual(calls[0]['payload']['task_id'], task['id'])

    def test_cancel_wins_over_late_result(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'open_website',
                                        {'url': 'https://example.com'})
        self.service.cancel_task(self.owner, task['id'])
        out = self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': task['id'], 'status': 'succeeded', 'data_json': '{}', 'evidence_json': '{}'})
        self.assertTrue(out.get('ignored'))
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'cancelled')
        with self.assertRaises(ApiError) as ctx:
            self.service.cancel_task(self.owner, str(uuid.uuid4()))
        self.assertEqual(ctx.exception.status, 404)

    def test_tool_result_drives_search_and_failure(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                        {'query': 'brief'})
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': task['id'], 'status': 'succeeded',
            'data_json': json.dumps({'candidates': [{'candidate_id': 'c1', 'name': 'b.txt'}]}),
            'evidence_json': '{}'})
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'awaiting_approval')
        self.assertEqual(row['result']['matches'], ['b.txt'])
        failed = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                          {'query': 'zzz'})
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': failed['id'], 'status': 'failed', 'error_code': 'no_match'})
        row = self.db.db('tasks', {'id': 'eq.' + failed['id']})[0]
        self.assertEqual(row['status'], 'failed')
        with self.assertRaises(ApiError) as ctx:
            self.service.complete_tool_result(self.owner, self.device['id'], {
                'task_id': str(uuid.uuid4()), 'status': 'succeeded'})
        self.assertEqual(ctx.exception.status, 404)

    def test_completion_runs_outcome_checks(self):
        empty = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                         {'query': 'zzz'})
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': empty['id'], 'status': 'succeeded',
            'data_json': json.dumps({'candidates': []}), 'evidence_json': '{}'})
        row = self.db.db('tasks', {'id': 'eq.' + empty['id']})[0]
        self.assertEqual((row['status'], row['result']['error_code']), ('failed', 'no_match'))
        send = self.service.create_task(self.owner, self.device['id'], '', 'send_file',
                                        {'candidate_id': 'c1', 'approval_id': 'a1'})
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': send['id'], 'status': 'succeeded',
            'data_json': json.dumps({'name': 'x'}), 'evidence_json': json.dumps(
                {'candidate_id': 'other-file'})})
        row = self.db.db('tasks', {'id': 'eq.' + send['id']})[0]
        self.assertEqual((row['status'], row['result']['error_code']),
                         ('failed', 'candidate_changed'))
        fs_task = self.db.db('tasks', body={
            'user_id': self.owner, 'device_id': self.device['id'], 'kind': 'fs_write',
            'input': {}, 'status': 'queued'}, method='POST')[0]
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': fs_task['id'], 'status': 'succeeded',
            'data_json': json.dumps({'path': 'n.txt'}), 'evidence_json': '{}'})
        row = self.db.db('tasks', {'id': 'eq.' + fs_task['id']})[0]
        self.assertEqual((row['status'], row['result']['error_code']),
                         ('failed', 'invalid_message'))

    def test_transfer_receipt_verifies_both_directions(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'send_file',
                                        {'candidate_id': 'c1', 'approval_id': 'a1'})
        raw = b'hello pico!'
        digest_value = hashlib.sha256(raw).hexdigest()
        self.db.db('tasks', {'id': 'eq.' + task['id']}, {
            'status': 'verifying',
            'result': {'file_path': 'owner-1/x', 'name': 'h.txt',
                       'size_bytes': len(raw), 'digest': digest_value}}, 'PATCH')
        out = self.service.submit_receipt(self.owner, {
            'task_id': task['id'], 'size_bytes': len(raw), 'digest': digest_value})
        self.assertTrue(out['verified'])
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        task2 = self.service.create_task(self.owner, self.device['id'], '', 'send_file',
                                         {'candidate_id': 'c2', 'approval_id': 'a2'})
        self.db.db('tasks', {'id': 'eq.' + task2['id']}, {
            'status': 'verifying',
            'result': {'size_bytes': 3, 'digest': 'abc'}}, 'PATCH')
        with self.assertRaises(ApiError):
            self.service.submit_receipt(self.owner, {
                'task_id': task2['id'], 'size_bytes': 3, 'digest': 'wrong'})
        row = self.db.db('tasks', {'id': 'eq.' + task2['id']})[0]
        self.assertEqual(row['status'], 'failed')

    def test_upload_transfer_rejects_before_network(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'send_file',
                                        {'candidate_id': 'c1', 'approval_id': 'a1'})
        find = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                        {'query': 'q'})
        with self.assertRaises(ApiError):
            self.service.upload_transfer(self.owner, self.device['id'], {'task_id': find['id']})
        with self.assertRaises(ApiError):
            self.service.upload_transfer(self.owner, self.device['id'], {
                'task_id': task['id'], 'content_base64': '!!!'})
        good = base64.b64encode(b'0123456789').decode()
        with self.assertRaises(ApiError):
            self.service.upload_transfer(self.owner, self.device['id'], {
                'task_id': task['id'], 'content_base64': good,
                'size_bytes': 999, 'digest': hashlib.sha256(b'0123456789').hexdigest()})
        with self.assertRaises(ApiError):
            self.service.upload_transfer(self.owner, self.device['id'], {
                'task_id': task['id'], 'content_base64': good,
                'size_bytes': 10, 'digest': '0' * 64})
        big = base64.b64encode(b'x' * (1024 * 1024 + 1)).decode()
        with self.assertRaises(ApiError):
            self.service.upload_transfer(self.owner, self.device['id'], {
                'task_id': task['id'], 'content_base64': big,
                'size_bytes': 1024 * 1024 + 1, 'digest': 'x'})
        self.service.cancel_task(self.owner, task['id'])
        out = self.service.upload_transfer(self.owner, self.device['id'], {'task_id': task['id']})
        self.assertTrue(out.get('ignored'))

    def test_cancel_removes_queued_calls_and_signals_helper(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                        {'query': 'brief'})
        queued = [m for m in self.service.mailbox(self.owner, self.device['id'])
                  if m['kind'] == 'tool_call']
        self.assertEqual(len(queued), 1)
        receipt = self.service.cancel_task(self.owner, task['id'])
        self.assertEqual((receipt['removed_queued'], receipt['notified_helper']), (1, True))
        mail = self.service.mailbox(self.owner, self.device['id'])
        self.assertFalse(any(m['kind'] == 'tool_call' for m in mail))
        cancels = [m for m in mail if m['kind'] == 'cancel']
        self.assertEqual(cancels[0]['payload']['task_id'], task['id'])
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'cancelled')
        self.assertIn('removed 1 queued', row['result']['message'])

    def test_create_note_validates_names(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'create_note',
                                        {'name': 'meeting-notes.txt', 'text': 'hi'})
        queued = [m for m in self.service.mailbox(self.owner, self.device['id'])
                  if m['kind'] == 'tool_call']
        self.assertEqual(queued[0]['payload']['path'], 'meeting-notes.txt')
        self.assertEqual(queued[0]['payload']['content'], 'hi')
        for bad in ('', '../escape.txt', 'sub/dir.txt', '.hidden', 'a/b'):
            with self.assertRaises(ApiError) as ctx:
                self.service.create_task(self.owner, self.device['id'], '', 'create_note',
                                         {'name': bad})
            self.assertEqual(ctx.exception.status, 400)

    def test_upload_artifact_stores_dedupes_and_scopes(self):
        raw = b'\xff\xd8\xff' + bytes(range(256))
        body = base64.b64encode(raw).decode()
        digest_value = hashlib.sha256(raw).hexdigest()
        out = self.service.upload_artifact(
            self.owner, self.device['id'], '', 'photo.jpg', body, 'transfer')
        self.assertEqual(out['artifact_id'], digest_value)
        self.assertEqual(out['size_bytes'], len(raw))
        self.assertFalse(out['duplicate'])
        again = self.service.upload_artifact(
            self.owner, self.device['id'], '', 'photo.jpg', body, 'transfer')
        self.assertTrue(again['duplicate'])
        self.assertEqual(again['artifact_id'], digest_value)
        stored = [key for key in self.db.objects if key[0] == self.owner]
        self.assertEqual(len(stored), 1)
        queued = [m for m in self.service.mailbox(self.owner, self.device['id'])
                  if m['kind'] == 'tool_call']
        self.assertEqual(queued[0]['payload']['tool'], 'fetch_upload')
        fetched = self.service.artifact_for_helper(
            self.owner, self.device['id'], digest_value)
        self.assertEqual(base64.b64decode(fetched['content_base64']), raw)
        with self.assertRaises(ApiError) as ctx:
            self.service.artifact_for_helper(self.owner, self.device['id'], '0' * 64)
        self.assertEqual(ctx.exception.status, 404)
        with self.assertRaises(ApiError) as ctx:
            self.service.artifact_for_helper('owner-2', self.device['id'], digest_value)
        self.assertEqual(ctx.exception.status, 404)
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as storage:
            self.service.uploads.get('owner-2', digest_value)
        self.assertEqual(storage.exception.code, 404)
        with self.assertRaises(ApiError) as ctx:
            self.service.artifact_for_helper(self.owner, self.device['id'], 'nope')
        self.assertEqual(ctx.exception.status, 400)

    def test_upload_artifact_validates_input(self):
        body = base64.b64encode(b'x').decode()
        cases = [
            ('photo.jpg', '!!!not-base64!!!', 'transfer', 400),
            ('photo.jpg', '', 'transfer', 400),
            ('photo.jpg', base64.b64encode(bytes(1024 * 1024 + 1)).decode(),
             'transfer', 400),
            ('../escape.jpg', body, 'transfer', 400),
            ('photo.jpg', body, 'read', 400),
            ('photo.jpg', body, None, 400),
        ]
        for name, content, purpose, status in cases:
            with self.assertRaises(ApiError) as ctx:
                self.service.upload_artifact(
                    self.owner, self.device['id'], '', name, content, purpose)
            self.assertEqual(ctx.exception.status, status, name)
        with self.assertRaises(ApiError):
            self.service.upload_artifact(
                self.owner, str(uuid.uuid4()), '', 'photo.jpg', body, 'transfer')

    def test_open_document_task_validates_and_completes(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'open_document',
                                        {'query': 'quarterly report'})
        queued = [m for m in self.service.mailbox(self.owner, self.device['id'])
                  if m['kind'] == 'tool_call']
        self.assertEqual(queued[0]['payload']['query'], 'quarterly report')
        with self.assertRaises(ApiError) as ctx:
            self.service.create_task(self.owner, self.device['id'], '', 'open_document',
                                     {'query': '  '})
        self.assertEqual(ctx.exception.status, 400)
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': task['id'], 'status': 'succeeded',
            'data_json': json.dumps({'name': 'report.docx', 'candidate_id': 'c1'}),
            'evidence_json': json.dumps({'candidate_id': 'c1'})})
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('Opened report.docx', row['result']['message'])
        bad_task = self.service.create_task(self.owner, self.device['id'], '',
                                            'open_document', {'query': 'x'})
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': bad_task['id'], 'status': 'succeeded',
            'data_json': json.dumps({'name': 'x'}), 'evidence_json': '{}'})
        row = self.db.db('tasks', {'id': 'eq.' + bad_task['id']})[0]
        self.assertEqual((row['status'], row['result']['error_code']),
                         ('failed', 'invalid_message'))

    def test_organize_task_validates_folder(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'organize_photos',
                                        {'folder': 'Santosh_Photos'})
        queued = [m for m in self.service.mailbox(self.owner, self.device['id'])
                  if m['kind'] == 'tool_call']
        self.assertEqual(queued[0]['payload']['folder'], 'Santosh_Photos')
        self.assertEqual(task['kind'], 'organize_photos')
        for bad in ('', '../out', 'a/b', '.hidden'):
            with self.assertRaises(ApiError) as ctx:
                self.service.create_task(self.owner, self.device['id'], '',
                                         'organize_photos', {'folder': bad})
            self.assertEqual(ctx.exception.status, 400)
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': task['id'], 'status': 'succeeded',
            'data_json': json.dumps({'folder': 'Santosh_Photos', 'copied_count': 2,
                                     'duplicates_skipped': 1, 'found': 3}),
            'evidence_json': json.dumps({'count': 2})})
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'completed')
        self.assertIn('Gathered 2 photo(s)', row['result']['message'])
        bad_task = self.service.create_task(self.owner, self.device['id'], '',
                                            'organize_photos', {'folder': 'Pics'})
        self.service.complete_tool_result(self.owner, self.device['id'], {
            'task_id': bad_task['id'], 'status': 'succeeded',
            'data_json': json.dumps({'folder': 'Pics'}), 'evidence_json': '{}'})
        row = self.db.db('tasks', {'id': 'eq.' + bad_task['id']})[0]
        self.assertEqual((row['status'], row['result']['error_code']),
                         ('failed', 'invalid_message'))

    def test_steer_rejections_are_honest(self):
        search = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                          {'query': 'brief'})
        with self.assertRaises(ApiError) as ctx:
            self.service.steer_task(self.owner, search['id'], 'note.txt')
        self.assertEqual(ctx.exception.status, 409)
        note = self.service.create_task(self.owner, self.device['id'], '', 'create_note',
                                        {'name': 'draft.txt'})
        with self.assertRaises(ApiError) as ctx:
            self.service.steer_task(self.owner, note['id'], '../escape.txt')
        self.assertEqual(ctx.exception.status, 400)
        with self.assertRaises(ApiError) as ctx:
            self.service.steer_task(self.owner, str(uuid.uuid4()), 'note.txt')
        self.assertEqual(ctx.exception.status, 404)
        mail = self.service.mailbox(self.owner, self.device['id'])
        self.service.acknowledge(self.owner, self.device['id'],
                                 [m['id'] for m in mail if m['kind'] == 'tool_call'
                                  and m['payload'].get('task_id') == note['id']])
        with self.assertRaises(ApiError) as ctx:
            self.service.steer_task(self.owner, note['id'], 'final.txt')
        self.assertEqual(ctx.exception.status, 409)
        self.assertIn('picked this up', ctx.exception.message)
        self.service.cancel_task(self.owner, note['id'])
        with self.assertRaises(ApiError) as ctx:
            self.service.steer_task(self.owner, note['id'], 'final.txt')
        self.assertEqual(ctx.exception.status, 409)

    def test_cancel_lands_when_device_gone(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'find_document',
                                        {'query': 'brief'})
        self.db.db('devices', {'id': 'eq.' + self.device['id']},
                   {'revoked_at': 'now'}, 'PATCH')
        receipt = self.service.cancel_task(self.owner, task['id'])
        self.assertFalse(receipt['notified_helper'])
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertEqual(row['status'], 'cancelled')

    def test_delete_transfer_and_clear_history(self):
        task = self.service.create_task(self.owner, self.device['id'], '', 'send_file',
                                        {'candidate_id': 'c1', 'approval_id': 'a1'})
        self.db.db('tasks', {'id': 'eq.' + task['id']},
                   {'result': {'file_path': 'owner-1/x', 'name': 'h.txt'}}, 'PATCH')
        self.service.delete_transfer(self.owner, task['id'])
        row = self.db.db('tasks', {'id': 'eq.' + task['id']})[0]
        self.assertNotIn('file_path', row['result'])
        self.service.clear_history(self.owner)
        self.assertEqual(self.db.db('tasks', {'user_id': 'eq.' + self.owner}), [])

    def test_upload_merge_preserves_early_excerpt(self):
        merged = merge_upload_result(
            {'excerpt': 'hi', 'name': 'old'},
            {'file_path': 'p', 'name': 'new', 'size_bytes': 1, 'digest': 'd'})
        self.assertEqual((merged['excerpt'], merged['name'], merged['digest']),
                         ('hi', 'new', 'd'))
        self.assertEqual(merge_upload_result(None, {'file_path': 'p'})['file_path'], 'p')

    def test_mail_and_tasks_survive_service_restart(self):
        from relay.state import RelayState as State
        import tempfile
        first = PicoService(self.db, self.service.state)
        first.enqueue(self.owner, self.device['id'], 'place',
                      {'place_id': 'p1', 'sentence': 'hi'})
        task = first.create_task(self.owner, self.device['id'], '', 'find_document',
                                 {'query': 'brief'})
        with tempfile.TemporaryDirectory(prefix='pico-restart-') as tmp:
            second = PicoService(self.db, State(Path(tmp) / 'fresh.sqlite'))
            mail = second.mailbox(self.owner, self.device['id'])
            self.assertTrue(any(m['kind'] == 'place' for m in mail))
            rows = second.db.db('tasks', {'id': 'eq.' + task['id']})
            self.assertEqual(rows[0]['status'], 'queued')
            ids = [m['id'] for m in mail]
            second.acknowledge(self.owner, self.device['id'], ids)
            second.acknowledge(self.owner, self.device['id'], ids)
            self.assertEqual(second.mailbox(self.owner, self.device['id']), [])

    def test_access_line_never_logs_query_or_tokens(self):
        line = access_line('GET', '/task?id=secret&code=123456', 200, 12)
        self.assertEqual(line, 'GET /task 200 12ms')
        self.assertNotIn('secret', line)
        self.assertEqual(access_line('POST', '', 404, 1), 'POST / 404 1ms')


if __name__ == '__main__':
    unittest.main()
