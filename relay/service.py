"""Pico's text mailbox over the existing project. No changes to existing schemas or unrelated rows."""
import hashlib
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

CHARACTERS = ('tuck', 'mica')
SIZES = ('small', 'medium', 'large')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identifier(value):
    return str(uuid.UUID(str(value)))


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
        from .mailbox import Mailbox
        self.mail = Mailbox(database)
        self.mail.ensure()

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
        return self.db.db('devices', {'user_id': 'eq.'+owner, 'revoked_at': 'is.null', 'name': 'like.Pico · *', 'select': 'id,name,os,last_seen', 'order': 'created_at.desc'})

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
        if kind not in ('place', 'companion', 'idle', 'head_start', 'parked'):
            raise ApiError(400, 'Unsupported Pico message.')
        allowed = {'place_id', 'sentence', 'character', 'size', 'app', 'head_start', 'mood', 'mood_until'}
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
