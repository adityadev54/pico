"""Run with python3 -m relay.app --env-file /path/to/server.env."""
import argparse
import json
import shutil
import mimetypes
import os
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .service import ApiError, PicoService, Supabase, identifier, stamp
from .state import RelayState

ROOT = Path(__file__).resolve().parents[1]


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Codes, tokens, queries and user text never enter request logs.

        def headers_for(self, type='application/json'):
            self.send_header('Content-Type', type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('X-Content-Type-Options', 'nosniff')

        def send(self, status, body):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.headers_for()
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            self.send_response(204)
            self.headers_for()
            self.end_headers()

        def do_GET(self):
            self.handle_request('GET')

        def do_POST(self):
            self.handle_request('POST')

        def handle_request(self, method):
            try:
                path = urllib.parse.urlsplit(self.path).path
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                body = {}
                if method == 'POST':
                    length = int(self.headers.get('Content-Length', 0))
                    if length < 0 or length > 16000:
                        raise ApiError(413, 'Pico accepts short text messages only.')
                    body = json.loads(self.rfile.read(length) or b'{}')
                    if not isinstance(body, dict):
                        raise ApiError(400, 'Expected a message object.')
                if method == 'GET' and path == '/health':
                    # This checks real DB reachability, without reading user content.
                    service.db.db('devices', {'select': 'id', 'limit': '0'})
                    return self.send(200, {'status': 'ok', 'product': 'pico', 'supabase_connected': True, 'snapshots_on_server': False})
                if method == 'POST' and path == '/claim':
                    return self.send(200, service.claim(body, self.headers.get('Fly-Client-IP', self.client_address[0]) if os.environ.get('FLY_APP_NAME') else self.client_address[0]))
                if path.startswith('/agent/'):
                    device = service.device(token)
                    owner, id = device['user_id'], device['id']
                    if path == '/agent/poll' and method == 'POST':
                        service.db.db('devices', {'id': 'eq.'+id}, {'last_seen': stamp()}, 'PATCH')
                        return self.send(200, {'mail': service.mailbox(owner, id), 'device_id': id})
                    if path == '/agent/ack' and method == 'POST':
                        return self.send(200, service.acknowledge(owner, id, body.get('ids', [])))
                    if path == '/agent/mail' and method == 'POST':
                        if body.get('kind') not in ('idle', 'head_start', 'parked'):
                            raise ApiError(400, 'Unsupported computer message.')
                        return self.send(200, service.enqueue(owner, id, body['kind'], body.get('payload', {}), body.get('id'), phone=True))
                    if path == '/agent/revoke' and method == 'POST':
                        return self.send(200, service.revoke(owner, id))
                if path in ('/devices', '/pairing', '/mail', '/receipts', '/unpair', '/phone/mail', '/phone/ack'):
                    owner = service.user(token)
                    if path == '/devices' and method == 'GET':
                        return self.send(200, {'devices': service.devices(owner)})
                    if path == '/pairing' and method == 'POST':
                        return self.send(200, service.pairing(owner))
                    if path == '/mail' and method == 'POST':
                        if body.get('kind') not in ('place', 'companion'):
                            raise ApiError(400, 'Unsupported phone message.')
                        return self.send(200, service.enqueue(owner, identifier(body.get('device_id')), body['kind'], body.get('payload', {}), body.get('id')))
                    if path == '/unpair' and method == 'POST':
                        return self.send(200, service.revoke(owner, identifier(body.get('device_id'))))
                    if path == '/receipts' and method == 'POST':
                        ids = body.get('ids', [])
                        if not isinstance(ids, list) or len(ids) > 100:
                            raise ApiError(400, 'Invalid receipt list.')
                        return self.send(200, {'delivered': [id for id in ids if service.state.received(owner, identifier(id))]})
                    if path == '/phone/mail' and method == 'GET':
                        items = []
                        for device in service.devices(owner):
                            items.extend(service.mailbox(owner, device['id'], phone=True))
                        return self.send(200, {'mail': items})
                    if path == '/phone/ack' and method == 'POST':
                        id = identifier(body.get('device_id'))
                        service.owned(owner, id)
                        return self.send(200, service.acknowledge(owner, id, body.get('ids', []), phone=True))
                if method == 'GET' and self.static(path):
                    return
                self.send(404, {'error': 'Not found'})
            except ApiError as error:
                self.send(error.status, {'error': error.message})
            except (ValueError, KeyError, TypeError):
                self.send(400, {'error': 'Invalid Pico message.'})
            except (urllib.error.URLError, TimeoutError, OSError):
                self.send(503, {'error': 'Connection unavailable. Your work stays saved locally.'})
            except Exception:
                self.send(500, {'error': 'Pico could not complete this request.'})

        def static(self, path):
            if path in ('/', '/setup'):
                file = ROOT/'website/index.html'
            elif path.startswith('/phone'):
                relative = path.removeprefix('/phone').lstrip('/') or 'index.html'
                base = (ROOT/'build/web').resolve()
                file = (base/relative).resolve()
                if not file.is_relative_to(base):
                    return False
                if not file.is_file() and '.' not in Path(relative).name:
                    file = base/'index.html'
            elif path.startswith('/download/'):
                filename = path.removeprefix('/download/')
                if filename not in ('Pico-macOS.zip','Pico-Windows.zip','Pico-source.zip','Pico-macOS.dmg','Pico-Setup.exe','Pico-Android.apk','SHA256SUMS'):
                    return False
                file = ROOT/'downloads'/filename
            elif path.startswith('/characters/'):
                parts = path.removeprefix('/characters/').split('/')
                if len(parts) != 2 or parts[0] not in ('tuck','mica') or parts[1] not in ('idle.gif','idle.png','working.gif','needsYou.gif'):
                    return False
                file = ROOT/'assets/characters'/parts[0]/parts[1]
            else:
                base = (ROOT/'website').resolve()
                file = (base/path.lstrip('/')).resolve()
                if not file.is_relative_to(base):
                    return False
            if not file.is_file():
                return False
            self.send_response(200)
            self.headers_for('application/vnd.android.package-archive' if file.suffix == '.apk' else mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(file.stat().st_size))
            self.end_headers()
            with file.open('rb') as stream:
                shutil.copyfileobj(stream, self.wfile, length=256*1024)
            return True
    return Handler


def load_env(file):
    if file:
        for line in Path(file).read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    parser = argparse.ArgumentParser(description='Pico text mailbox; existing Supabase project, no schema changes.')
    parser.add_argument('--env-file', default=os.environ.get('PICO_ENV_FILE'))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--state', default=str(ROOT/'.local/relay.sqlite'))
    args = parser.parse_args()
    load_env(args.env_file)
    url, key = os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise SystemExit('Set server-only SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, or pass --env-file.')
    service = PicoService(Supabase(url, key), RelayState(args.state))
    print(f'Pico relay: http://{args.host}:{args.port} · existing Supabase project · no screenshot uploads', flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(service)).serve_forever()

if __name__ == '__main__':
    main()
