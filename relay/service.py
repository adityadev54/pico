"""Pico's text mailbox over the existing project. No changes to existing schemas or unrelated rows."""
import base64
import hashlib
import json
import re
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

CHARACTERS = ('tuck', 'mica')
SIZES = ('small', 'medium', 'large')
# Contract tool vocabulary. Must match server.contract.SUPPORTED_TOOLS and
# agents.tools.TOOL_REGISTRY names (see agents/tests/test_tools.py).
TOOL_NAMES = ('search_documents', 'transfer_selected_file', 'capture_current_tab',
              'create_checklist', 'read_back_file', 'open_resource',
              'open_app', 'open_website', 'manage_permissions',
              'fs_list', 'fs_read', 'fs_write', 'process_run', 'fetch_upload',
              'organize_photos', 'open_document')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def merge_upload_result(existing, stored):
    """Merge stored file facts over any existing result (e.g. an excerpt
    that arrived via tool_result first). Stored facts always win."""
    merged = dict(existing or {})
    merged.update(stored)
    return merged


def identifier(value):
    return str(uuid.UUID(str(value)))


def clean_note_name(value):
    """Flat workspace-relative note name. Refuses traversal, folders,
    hidden files and empty names; the helper grant check still applies."""
    name = str(value or '').strip().strip('"\'').strip()[:128]
    if not name or '/' in name or '\\' in name or name.startswith('.'):
        raise ApiError(400, 'Give the note a simple filename.')
    return name


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class Supabase:
    def __init__(self, url, key):
        self.url, self.key = url.rstrip('/'), key

    def request(self, path, body=None, method='GET', token=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.url+path, data=data, method=method, headers={
            'apikey': self.key, 'Authorization': 'Bearer '+(token or self.key),
            'Content-Type': 'application/json', 'Prefer': 'return=representation',
        })
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    def db(self, table, filters=None, body=None, method='GET'):
        query = urllib.parse.urlencode(filters or {}, safe='.*,():')
        return self.request('/rest/v1/'+table+('?' + query if query else ''), body, method)


class PicoService:
    def __init__(self, database, state):
        self.db, self.state = database, state
        self.lock = threading.RLock()
        from .mailbox import Mailbox, Uploads
        self.mail = Mailbox(database)
        self.mail.ensure()
        self.uploads = Uploads(database)
        self.uploads.ensure()

    def user(self, token):
        if not token:
            raise ApiError(401, 'Sign in on your phone.')
        try:
            return self.db.request('/auth/v1/user', token=token)['id']
        except (urllib.error.HTTPError, KeyError):
            raise ApiError(401, 'Your session expired. Sign in again.') from None

    def device(self, token):
        if not token.startswith('pico_'):
            raise ApiError(401, 'Reconnect this computer.')
        rows = self.db.db('agent_credentials', {'token_hash': 'eq.'+digest('pico:'+token), 'select': 'device_id'})
        if rows:
            devices = self.db.db('devices', {'id': 'eq.'+rows[0]['device_id'], 'revoked_at': 'is.null', 'name': 'like.Pico · *'})
            if devices:
                return devices[0]
        raise ApiError(401, 'This computer was unpaired.')

    def devices(self, owner):
        try:
            return self.db.db('devices', {'user_id': 'eq.'+owner, 'revoked_at': 'is.null', 'name': 'like.Pico · *', 'select': 'id,name,os,last_seen,helper_version', 'order': 'created_at.desc'})
        except urllib.error.HTTPError as error:
            if error.code == 400:
                # Older projects lack helper_version; phone treats missing as outdated.
                return self.db.db('devices', {'user_id': 'eq.'+owner, 'revoked_at': 'is.null', 'name': 'like.Pico · *', 'select': 'id,name,os,last_seen', 'order': 'created_at.desc'})
            raise

    def owned(self, owner, id):
        id = identifier(id)
        rows = [d for d in self.devices(owner) if d['id'] == id]
        if not rows:
            raise ApiError(404, 'Computer not found. Connect it again.')
        return rows[0]

    def pairing(self, owner):
        with self.lock:
            if self.devices(owner):
                raise ApiError(409, 'Unpair your current computer before connecting another.')
            # Codes are namespaced by their hash. Existing connection codes are untouched.
            for _ in range(20):
                code = str(secrets.randbelow(1000000)).zfill(6)
                key = digest('pico:'+code)
                existing = self.db.db('pairing_codes', {'code_hash': 'eq.'+key})
                if existing:
                    if existing[0]['expires_at'] > stamp() and not existing[0]['claimed_at']:
                        continue
                    self.db.db('pairing_codes', {'code_hash': 'eq.'+key}, method='DELETE')
                expires = (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
                self.db.db('pairing_codes', body={'code_hash': key, 'user_id': owner, 'expires_at': expires}, method='POST')
                return {'code': code, 'expires_at': expires}
        raise ApiError(503, 'Could not make a code. Try again shortly.')

    def claim(self, body, address):
        if self.state.blocked(address):
            raise ApiError(429, 'Too many incorrect codes. Try again in 10 minutes.')
        code = str(body.get('code', ''))
        if len(code) != 6 or not code.isdigit() or body.get('os') not in ('macos', 'windows'):
            self.state.attempt(address)
            raise ApiError(400, 'Enter the 6-digit code from your phone.')
        with self.lock:
            key = digest('pico:'+code)
            rows = self.db.db('pairing_codes', {'code_hash': 'eq.'+key, 'claimed_at': 'is.null', 'expires_at': 'gt.'+stamp()})
            if not rows:
                self.state.attempt(address)
                raise ApiError(400, 'This code is incorrect, expired, or already used.')
            if self.devices(rows[0]['user_id']):
                raise ApiError(409, 'Unpair the existing computer first.')
            token = 'pico_'+secrets.token_urlsafe(48)
            name = 'Pico · '+str(body.get('name') or body['os']).strip()[:65]
            try:
                id = self.db.db('rpc/claim_pairing', body={'p_hash': key, 'p_name': name, 'p_os': body['os'], 'p_token_hash': digest('pico:'+token)}, method='POST')
            except urllib.error.HTTPError:
                self.state.attempt(address)
                raise ApiError(400, 'This code is no longer available. Get a new code.') from None
            self.state.attempt(address, success=True)
            return {'device_id': id, 'token': token, 'name': name}

    def enqueue(self, owner, device_id, kind, payload, id=None, phone=False):
        self.owned(owner, device_id)
        if kind not in ('place', 'companion', 'idle', 'head_start', 'parked', 'tool_call', 'tool_result', 'cancel'):
            raise ApiError(400, 'Unsupported Pico message.')
        allowed = {'place_id', 'sentence', 'character', 'size', 'app', 'head_start', 'mood', 'mood_until',
                   'task_id', 'tool', 'call_id', 'status', 'error_code', 'query', 'candidate_id',
                   'approval_id', 'url', 'grant_id', 'data_json', 'evidence_json', 'message',
                   'path', 'content', 'base_revision', 'argv_json', 'timeout_s', 'cwd',
                   'artifact_id', 'folder'}
        if set(payload)-allowed:
            raise ApiError(400, 'The mailbox accepts short text only. No snapshots.')
        if any(not isinstance(value, str) or len(value) > 2000 for value in payload.values()):
            raise ApiError(400, 'Keep each message below 2,000 characters.')
        if 'character' in payload and payload['character'] not in CHARACTERS:
            raise ApiError(400, 'Unknown companion.')
        if 'mood' in payload and payload['mood'] not in ('idle','listening','talking','working','thinking','done','stuck','needsYou'):
            raise ApiError(400, 'Unknown agent state.')
        if 'mood_until' in payload:
            try: expiry=int(payload['mood_until'])
            except ValueError: raise ApiError(400, 'Invalid state expiry.') from None
            if expiry > int(datetime.now(timezone.utc).timestamp()*1000)+90000:
                raise ApiError(400, 'Agent state expires within 90 seconds.')
        if 'size' in payload and payload['size'] not in SIZES:
            raise ApiError(400, 'Unknown character size.')
        if kind == 'tool_call' and payload.get('tool') not in TOOL_NAMES:
            raise ApiError(400, 'Unsupported tool.')
        if kind == 'tool_result' and payload.get('status') not in ('succeeded', 'failed', 'denied'):
            raise ApiError(400, 'Invalid tool result status.')
        id = identifier(id or uuid.uuid4())
        # Include owner/device/kind to prevent cross-device ID reuse.
        mail_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'pico/{owner}/{device_id}/{kind}/{id}/{phone}'))
        if self.state.received(owner, mail_id):
            return {'id': mail_id, 'status': 'delivered'}
        message = {'kind': kind, 'device_id': device_id, 'payload': payload}
        with self.lock:
            if kind == 'companion':
                previous = self.mail.list(owner, device_id, phone)
                self.mail.delete(owner, device_id, [m['id'] for m in previous if m['kind'] == 'companion'], phone)
            self.mail.put(owner, device_id, mail_id, message, phone)
        return {'id': mail_id, 'status': 'queued'}

    def mailbox(self, owner, device_id, phone=False):
        return self.mail.list(owner, device_id, phone)

    def acknowledge(self, owner, device_id, ids, phone=False):
        if not isinstance(ids, list) or len(ids) > 30:
            raise ApiError(400, 'Invalid receipt.')
        present = {m['id'] for m in self.mail.list(owner, device_id, phone)}
        accepted = [identifier(id) for id in ids if id in present]
        for id in accepted:
            self.state.delivered(owner, id)
        self.mail.delete(owner, device_id, accepted, phone)
        return {'ok': True}

    def revoke(self, owner, id):
        self.owned(owner, id)
        self.db.db('devices', {'id': 'eq.'+id, 'user_id': 'eq.'+owner}, {'revoked_at': stamp()}, 'PATCH')
        for phone in (False, True):
            while True:
                messages = self.mail.list(owner, id, phone)
                if not messages:break
                self.mail.delete(owner, id, [m['id'] for m in messages], phone)
        return {'ok': True}

    # --- Computer tasks (first integration) ---
    TASK_KINDS = ('find_document', 'send_file', 'open_website', 'open_app',
                  'manage_permissions', 'summarize_document', 'create_note',
                  'receive_upload', 'organize_photos', 'open_document')
    TOOL_FOR_KIND = {'find_document': 'search_documents', 'send_file': 'transfer_selected_file',
                     'open_website': 'open_website', 'open_app': 'open_app',
                     'manage_permissions': 'manage_permissions', 'summarize_document': 'read_back_file',
                     'create_note': 'fs_write', 'receive_upload': 'fetch_upload',
                     'organize_photos': 'organize_photos', 'open_document': 'open_document'}

    def create_task(self, owner, device_id, session_id, kind, input):
        device = self.owned(owner, identifier(device_id))
        if kind not in self.TASK_KINDS:
            raise ApiError(400, 'Unsupported request.')
        if not isinstance(input, dict):
            raise ApiError(400, 'Invalid request.')
        if device.get('helper_version') not in (None, '0.2.0', '0.3.0'):
            pass  # Old helpers still get text tasks; phone warns on open_app/permissions.
        tool = self.TOOL_FOR_KIND[kind]
        payload = {'task_id': str(uuid.uuid4()), 'tool': tool}
        if tool == 'search_documents':
            query = str(input.get('query', ''))[:500]
            if not query.strip():
                raise ApiError(400, 'What should I search for?')
            payload['query'] = query
        elif tool == 'transfer_selected_file':
            for key in ('candidate_id', 'approval_id'):
                value = str(input.get(key, ''))
                if not value:
                    raise ApiError(400, 'Select and approve a file first.')
                payload[key] = value[:128]
        elif tool == 'open_website':
            url = str(input.get('url', ''))[:2000]
            if not url.startswith(('https://', 'http://')):
                raise ApiError(400, 'Invalid website address.')
            payload['url'] = url
        elif tool == 'open_app':
            payload['app'] = str(input.get('app', ''))[:64] or 'browser'
        elif tool == 'fs_write':
            payload['path'] = clean_note_name(input.get('name', ''))
            payload['content'] = str(input.get('text', ''))[:2000]
        elif tool == 'fetch_upload':
            artifact = str(input.get('artifact_id', ''))
            if not re.fullmatch(r'[0-9a-f]{64}', artifact):
                raise ApiError(400, 'Invalid artifact reference.')
            payload['artifact_id'] = artifact
            payload['path'] = clean_note_name(input.get('name', ''))
        elif tool == 'organize_photos':
            payload['folder'] = clean_note_name(input.get('folder', ''))
        elif tool == 'open_document':
            query = str(input.get('query', ''))[:500]
            if not query.strip():
                raise ApiError(400, 'Name a document to open.')
            payload['query'] = query
        try:
            rows = self.db.db('tasks', body={
                'user_id': owner, 'device_id': device['id'],
                'session_id': str(session_id or '')[:128] or None,
                'kind': kind, 'input': input, 'status': 'queued',
            }, method='POST')
        except urllib.error.HTTPError as error:
            if error.code in (400, 404):
                raise ApiError(503, 'Tasks are not available in this project yet.') from None
            raise
        task = rows[0] if isinstance(rows, list) and rows else {'id': payload['task_id']}
        payload['task_id'] = task.get('id', payload['task_id'])
        payload['call_id'] = str(uuid.uuid4())
        try:
            self.enqueue(owner, device['id'], 'tool_call', payload, payload['call_id'])
        except ApiError:
            # Task row stays queued; computer picks it up on next poll retry.
            pass
        return task

    def cancel_task(self, owner, task_id):
        """Shared cancel path (A13): stop queued calls, signal running work,
        mark the row cancelled with a receipt naming what stopped."""
        rows = self.db.db('tasks', {'id': 'eq.'+identifier(task_id), 'user_id': 'eq.'+owner})
        if not rows:
            raise ApiError(404, 'Request not found.')
        task = rows[0]
        if task.get('status') in ('completed', 'failed', 'cancelled'):
            return {'ok': True}
        removed, notified = 0, False
        try:
            queued = [m for m in self.mail.list(owner, task['device_id'], False)
                      if m['kind'] == 'tool_call' and m['payload'].get('task_id') == task['id']]
            if queued:
                self.mail.delete(owner, task['device_id'], [m['id'] for m in queued], False)
                removed = len(queued)
            self.enqueue(owner, task['device_id'], 'cancel', {'task_id': task['id']})
            notified = True
        except Exception:
            pass  # Best effort: device gone or mailbox down, the row cancel still lands.
        if notified:
            message = (f'Cancelled: removed {removed} queued call(s); helper notified.'
                       if removed else 'Cancelled: helper notified; late results will be ignored.')
        else:
            message = 'Cancelled. Helper was unreachable; queued work stays cancelled.'
        result = dict(task.get('result') or {})
        result['message'] = message
        self.db.db('tasks', {'id': 'eq.'+task['id']},
                   {'status': 'cancelled', 'result': result}, 'PATCH')
        return {'ok': True, 'removed_queued': removed, 'notified_helper': notified}

    def steer_task(self, owner, task_id, name):
        """Mid-task steering (A13): rename the output target of a queued
        note before the helper picks it up. Rewrites the queued call and
        the task input; anything already picked up or decided gets an
        honest 409 instead of a silent miss."""
        rows = self.db.db('tasks', {'id': 'eq.'+identifier(task_id), 'user_id': 'eq.'+owner})
        if not rows:
            raise ApiError(404, 'Request not found.')
        task = rows[0]
        if task.get('status') in ('completed', 'failed', 'cancelled'):
            raise ApiError(409, 'That request already finished; start a new note.')
        if task.get('kind') != 'create_note':
            raise ApiError(409, 'Only a queued note can be renamed.')
        target = clean_note_name(name)
        queued = [m for m in self.mail.list(owner, task['device_id'], False)
                  if m['kind'] == 'tool_call' and m['payload'].get('task_id') == task['id']]
        if not queued:
            raise ApiError(409, 'Your computer already picked this up; too late to rename.')
        with self.lock:
            for mail in queued:
                payload = dict(mail['payload'], path=target)
                self.mail.delete(owner, task['device_id'], [mail['id']], False)
                self.mail.put(owner, task['device_id'], mail['id'], {
                    'kind': 'tool_call', 'device_id': task['device_id'],
                    'payload': payload}, False)
        result = dict(task.get('result') or {})
        result['message'] = f'Steered: output renamed to {target} before the write.'
        self.db.db('tasks', {'id': 'eq.'+task['id']},
                   {'input': {**(task.get('input') or {}), 'name': target},
                    'result': result}, 'PATCH')
        return {'ok': True, 'steered': True, 'path': target}

    UPLOAD_LIMIT = 1024 * 1024

    def upload_artifact(self, owner, device_id, session_id, name, content_base64, purpose):
        """Phone uploads bytes for one computer (B07). The artifact id is the
        content digest, so retries dedupe instead of duplicating; objects live
        under the owner's prefix, so owners can never switch or read across."""
        device = self.owned(owner, identifier(device_id))
        if purpose != 'transfer':
            raise ApiError(400, 'Only transfer-to-computer uploads are supported yet.')
        filename = clean_note_name(name)
        try:
            raw = base64.b64decode(content_base64 or '', validate=True)
        except Exception:
            raise ApiError(400, 'Invalid file content.') from None
        if not raw or len(raw) > self.UPLOAD_LIMIT:
            raise ApiError(400, 'File must be 1 byte to 1 MB.')
        digest_value = hashlib.sha256(raw).hexdigest()
        duplicate = self.uploads.put(owner, digest_value, {
            'content_base64': base64.b64encode(raw).decode(),
            'digest': digest_value, 'name': filename, 'size_bytes': len(raw)})
        task = self.create_task(owner, device['id'], session_id, 'receive_upload',
                                {'artifact_id': digest_value, 'name': filename})
        return {'artifact_id': digest_value, 'size_bytes': len(raw),
                'digest': digest_value, 'task_id': task['id'],
                'duplicate': duplicate}

    def artifact_for_helper(self, owner, device_id, artifact_id):
        """Paired computer fetches one owned upload's bytes (B07)."""
        self.owned(owner, identifier(device_id))
        if not re.fullmatch(r'[0-9a-f]{64}', str(artifact_id or '')):
            raise ApiError(400, 'Invalid artifact reference.')
        try:
            obj = self.uploads.get(owner, artifact_id)
        except urllib.error.HTTPError as error:
            raise ApiError(404, 'Upload not found.') from error
        if obj.get('digest') != artifact_id:
            raise ApiError(404, 'Upload not found.')
        return {'content_base64': obj['content_base64'], 'digest': obj['digest'],
                'name': obj.get('name', 'file')}

    def delete_transfer(self, owner, task_id):
        rows = self.db.db('tasks', {'id': 'eq.'+identifier(task_id), 'user_id': 'eq.'+owner})
        if not rows:
            raise ApiError(404, 'Request not found.')
        result = rows[0].get('result') or {}
        path = result.get('file_path')
        if path:
            try:
                self.db.request('/storage/v1/object/pico-transfers', {'prefixes': [path]}, 'DELETE')
            except urllib.error.HTTPError:
                pass
            result.pop('file_path', None)
            self.db.db('tasks', {'id': 'eq.'+rows[0]['id']}, {'result': result}, 'PATCH')
        return {'ok': True}

    def clear_history(self, owner):
        self.db.db('tasks', {'user_id': 'eq.'+owner}, method='DELETE')
        return {'ok': True}

    def upload_transfer(self, owner, device_id, body):
        """Computer uploads exact approved file bytes (base64, <=1MB).

        Relay validates size/digest, stores in pico-transfers via service key,
        and marks the send_file task awaiting authenticated phone receipt.
        """
        import base64

        task_id = str(body.get('task_id', ''))
        rows = self.db.db('tasks', {'id': 'eq.'+identifier(task_id), 'user_id': 'eq.'+owner})
        if not rows:
            raise ApiError(404, 'Request not found.')
        task = rows[0]
        if task.get('status') in ('cancelled', 'completed', 'failed'):
            return {'ok': True, 'ignored': True}
        if task.get('kind') != 'send_file':
            raise ApiError(400, 'Not a transfer task.')
        try:
            raw = base64.b64decode(body.get('content_base64', ''), validate=True)
        except Exception:
            raise ApiError(400, 'Invalid file content.') from None
        if len(raw) > 1024 * 1024 or len(raw) == 0:
            raise ApiError(400, 'File must be 1 byte to 1 MB for demo transfer.')
        size, digest_value = int(body.get('size_bytes', -1)), str(body.get('digest', ''))
        if size != len(raw) or digest_value != hashlib.sha256(raw).hexdigest():
            raise ApiError(400, 'File changed before transfer.')
        name = str(body.get('name', 'file'))[:120] or 'file'
        storage_path = f'{owner}/{task["id"]}/{uuid.uuid4().hex[:8]}_{name}'.replace(' ', '_')
        try:
            self.db.request('/storage/v1/object/pico-transfers/' + storage_path, None, 'POST')
        except urllib.error.HTTPError:
            pass  # Bucket may need creation; upload below creates the object.
        # Raw binary upload via service key.
        import urllib.request as urlrequest
        req = urlrequest.Request(
            self.db.url + '/storage/v1/object/pico-transfers/' + storage_path,
            data=raw, method='POST',
            headers={'apikey': self.db.key, 'Authorization': 'Bearer ' + self.db.key,
                     'Content-Type': 'application/octet-stream'})
        try:
            with urlrequest.urlopen(req, timeout=30):
                pass
        except urllib.error.HTTPError as error:
            raise ApiError(503, 'Could not store the file. Try again.') from error
        self.db.db('tasks', {'id': 'eq.'+task['id']}, {
            'status': 'verifying',
            'result': merge_upload_result(task.get('result'), {
                'file_path': storage_path, 'name': name,
                'size_bytes': size, 'digest': digest_value})}, 'PATCH')
        return {'ok': True, 'file_path': storage_path}

    def submit_receipt(self, owner, body):
        """Authenticated phone acknowledges received size/digest; verifier checks both."""
        from server.verification.checks import check_transfer_receipt

        task_id = str(body.get('task_id', ''))
        rows = self.db.db('tasks', {'id': 'eq.'+identifier(task_id), 'user_id': 'eq.'+owner})
        if not rows:
            raise ApiError(404, 'Request not found.')
        task = rows[0]
        if task.get('status') in ('cancelled', 'completed', 'failed'):
            return {'ok': True}
        evidence = task.get('result') or {}
        receipt = {'authenticated': True,
                   'size_bytes': body.get('size_bytes'),
                   'digest': body.get('digest')}
        try:
            check_transfer_receipt(
                {'size_bytes': evidence.get('size_bytes'), 'digest': evidence.get('digest')},
                receipt)
        except Exception as error:
            code = getattr(error, 'code', 'candidate_changed')
            self.db.db('tasks', {'id': 'eq.'+task['id']},
                       {'status': 'failed', 'result': {**evidence, 'error_code': code}}, 'PATCH')
            raise ApiError(400, 'Received file does not match the approved file.') from None
        self.db.db('tasks', {'id': 'eq.'+task['id']},
                   {'status': 'completed',
                    'result': {**evidence, 'receipt': 'verified'}}, 'PATCH')
        return {'ok': True, 'verified': True}

    def complete_tool_result(self, owner, device_id, payload):
        """Computer posts tool_result; relay updates the owned task row.

        Late results after cancellation/completion are acknowledged but ignored.
        """
        task_id = payload.get('task_id', '')
        try:
            rows = self.db.db('tasks', {'id': 'eq.'+identifier(task_id), 'user_id': 'eq.'+owner})
        except ValueError:
            raise ApiError(400, 'Invalid task reference.') from None
        if not rows:
            raise ApiError(404, 'Request not found.')
        task = rows[0]
        if task.get('status') in ('cancelled', 'completed', 'failed'):
            return {'ok': True, 'ignored': True}
        status = payload.get('status')
        if status != 'succeeded':
            code = payload.get('error_code', 'timeout')
            self.db.db('tasks', {'id': 'eq.'+task['id']},
                       {'status': 'failed', 'result': {'error_code': code[:64]}}, 'PATCH')
            return {'ok': True}
        try:
            data = json.loads(payload.get('data_json', '{}') or '{}')
            evidence = json.loads(payload.get('evidence_json', '{}') or '{}')
        except ValueError:
            raise ApiError(400, 'Invalid tool data.') from None
        from server.contract import ContractError
        from server.verification.checks import (
            check_exact_file, check_fs_manifest, check_open_document,
            check_organize_manifest, check_process_result, check_search_outcome)
        kind = task.get('kind')
        try:
            if kind == 'find_document':
                check_search_outcome({'status': 'succeeded', 'data': data})
            elif kind == 'send_file':
                approved = (task.get('input') or {}).get('candidate_id')
                check_exact_file({'candidate_id': approved}, {'candidate_id': approved}, evidence)
            elif kind in ('fs_list', 'fs_read', 'fs_write', 'create_note',
                            'receive_upload'):
                check_fs_manifest(
                    data, 'fs_write' if kind in ('create_note', 'receive_upload') else kind)
            elif kind == 'process_run':
                check_process_result(data)
            elif kind == 'organize_photos':
                check_organize_manifest(data)
            elif kind == 'open_document':
                check_open_document(data)
            # open_website/open_app/manage_permissions/read_back_file carry no
            # checkable evidence; a succeeded report completes them.
        except ContractError as failed:
            self.db.db('tasks', {'id': 'eq.'+task['id']},
                       {'status': 'failed', 'result': {'error_code': failed.code}}, 'PATCH')
            return {'ok': True}
        if kind == 'find_document':
            candidates = data.get('candidates', [])[:20]
            self.db.db('tasks', {'id': 'eq.'+task['id']}, {
                'status': 'awaiting_approval',
                'result': {'matches': [c.get('name', '')[:120] for c in candidates],
                           'candidates': candidates, 'evidence': evidence}}, 'PATCH')
        elif kind == 'send_file':
            # Upload already stored file_path/size/digest; merge excerpt, await phone receipt.
            existing = task.get('result') or {}
            merged = {**existing, 'evidence': evidence,
                      'name': data.get('name', existing.get('name', ''))[:120]}
            if data.get('excerpt'):
                merged['excerpt'] = str(data['excerpt'])[:1500]
            self.db.db('tasks', {'id': 'eq.'+task['id']}, {
                'status': 'verifying', 'result': merged}, 'PATCH')
        elif kind == 'open_document':
            self.db.db('tasks', {'id': 'eq.'+task['id']}, {
                'status': 'completed',
                'result': {'evidence': evidence, **data,
                           'message': f'Opened {data.get("name")} on your computer.'}}, 'PATCH')
        elif kind == 'organize_photos':
            copied, dupes = data.get('copied_count', 0), data.get('duplicates_skipped', 0)
            self.db.db('tasks', {'id': 'eq.'+task['id']}, {
                'status': 'completed',
                'result': {'evidence': evidence, **data,
                           'message': f'Gathered {copied} photo(s) into {data.get("folder")}; '
                                      f'skipped {dupes} duplicate(s). Originals untouched.'}}, 'PATCH')
        else:
            merged = {'evidence': evidence, **data}
            prior = (task.get('result') or {}).get('message')
            if prior and 'message' not in merged:
                merged['message'] = prior  # Keep relay-side notes (e.g. steering).
            self.db.db('tasks', {'id': 'eq.'+task['id']}, {
                'status': 'completed', 'result': merged}, 'PATCH')
        return {'ok': True}
