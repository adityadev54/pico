import copy
import fnmatch
import urllib.error
import uuid
from datetime import datetime, timezone


def http_error(code):
    return urllib.error.HTTPError('fake', code, 'fake', {}, None)


class FakeSupabase:
    """In-memory Supabase double: REST tables, storage objects and claim RPC."""

    def __init__(self):
        self.tables = {
            'devices': [],
            'pairing_codes': [],
            'agent_credentials': [],
            'tasks': [],
            'handoffs': [],
        }
        self.objects = {}
        self.buckets = {'pico-mailbox': {'public': False}}
        self.helper_version_supported = True
        self.auth_user = 'owner-1'
        self.url, self.key = 'https://fake.supabase.co', 'fake-key'

    # ---- REST ----
    def db(self, table, filters=None, body=None, method='GET'):
        if table == 'rpc/claim_pairing':
            return self._rpc_claim(body)
        filters = filters or {}
        if 'helper_version' in str(filters.get('select', '')) and not self.helper_version_supported:
            raise http_error(400)
        rows = self.tables[table]
        if method == 'GET':
            return [copy.deepcopy(r) for r in rows if self._match(r, filters)]
        if method == 'POST':
            row = dict(body)
            row.setdefault('id', str(uuid.uuid4()))
            row.setdefault('created_at', datetime.now(timezone.utc).isoformat())
            rows.append(row)
            return [copy.deepcopy(row)]
        if method == 'PATCH':
            out = []
            for r in rows:
                if self._match(r, filters):
                    r.update(body)
                    out.append(copy.deepcopy(r))
            return out
        if method == 'DELETE':
            self.tables[table] = [r for r in rows if not self._match(r, filters)]
            return []
        raise AssertionError(method)

    def _match(self, row, filters):
        for key, cond in filters.items():
            if key in ('select', 'order', 'limit', 'offset'):
                continue
            value = row.get(key)
            if cond == 'is.null':
                if value is not None:
                    return False
            elif cond.startswith('eq.'):
                if str(value) != cond[3:]:
                    return False
            elif cond.startswith('gt.'):
                if not (str(value) > cond[3:]):
                    return False
            elif cond.startswith('like.'):
                if not fnmatch.fnmatchcase(str(value or ''), cond[5:]):
                    return False
            else:
                raise AssertionError(cond)
        return True

    def _rpc_claim(self, body):
        for row in self.tables['pairing_codes']:
            if (row['code_hash'] == body['p_hash'] and not row.get('claimed_at')
                    and row['expires_at'] > datetime.now(timezone.utc).isoformat()):
                break
        else:
            raise http_error(400)
        if any(d['user_id'] == row['user_id'] and not d.get('revoked_at')
               and fnmatch.fnmatchcase(d['name'], 'Pico · *') for d in self.tables['devices']):
            raise http_error(400)
        device_id = str(uuid.uuid4())
        self.tables['devices'].append({
            'id': device_id, 'user_id': row['user_id'], 'name': body['p_name'],
            'os': body['p_os'], 'revoked_at': None,
            'created_at': datetime.now(timezone.utc).isoformat()})
        self.tables['agent_credentials'].append(
            {'token_hash': body['p_token_hash'], 'device_id': device_id})
        row['claimed_at'] = datetime.now(timezone.utc).isoformat()
        return device_id

    # ---- storage / auth ----
    def request(self, path, body=None, method='GET', token=None):
        if path == '/auth/v1/user':
            if not token:
                raise http_error(401)
            return {'id': self.auth_user}
        if path == '/storage/v1/bucket/pico-mailbox':
            if 'pico-mailbox' not in self.buckets:
                raise http_error(404)
            return dict(self.buckets['pico-mailbox'])
        if path == '/storage/v1/bucket/pico-uploads':
            if 'pico-uploads' not in self.buckets:
                raise http_error(404)
            return dict(self.buckets['pico-uploads'])
        if path == '/storage/v1/bucket' and method == 'POST':
            self.buckets[body['id']] = dict(body)
            return dict(body)
        if path == '/storage/v1/object/list/pico-mailbox' and method == 'POST':
            return [{'name': name} for (prefix, name) in self.objects
                    if prefix == body['prefix']]
        if path == '/storage/v1/object/pico-mailbox' and method == 'DELETE':
            for key in body['prefixes']:
                prefix, name = key.rsplit('/', 1)
                self.objects.pop((prefix, name), None)
            return []
        if path == '/storage/v1/object/pico-transfers' and method == 'DELETE':
            return []
        if path.startswith('/storage/v1/object/pico-mailbox/'):
            rest = path.removeprefix('/storage/v1/object/pico-mailbox/')
            prefix, name = rest.rsplit('/', 1)
            if method == 'POST':
                if (prefix, name) in self.objects:
                    raise http_error(409)
                self.objects[(prefix, name)] = copy.deepcopy(body)
                return dict(body)
            if (prefix, name) not in self.objects:
                raise http_error(404)
            return copy.deepcopy(self.objects[(prefix, name)])
        if path.startswith('/storage/v1/object/pico-uploads/'):
            rest = path.removeprefix('/storage/v1/object/pico-uploads/')
            prefix, name = rest.rsplit('/', 1)
            if method == 'POST':
                if (prefix, name) in self.objects:
                    raise http_error(409)
                self.objects[(prefix, name)] = copy.deepcopy(body)
                return dict(body)
            if (prefix, name) not in self.objects:
                raise http_error(404)
            return copy.deepcopy(self.objects[(prefix, name)])
        if path.startswith('/storage/v1/object/pico-transfers/'):
            raise http_error(404)
        raise AssertionError(path)
