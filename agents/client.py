"""Device-only client. No account login or Supabase service key on the computer."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

class DeviceClient:
    def __init__(self, base, token='', device_id=''):
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1','localhost') or os.environ.get('PICO_ALLOW_LAN') == '1' and parsed.scheme == 'http'):
            raise ValueError('Use HTTPS, localhost, or explicitly enable LAN development with PICO_ALLOW_LAN=1.')
        self.base, self.token, self.device_id = base.rstrip('/'), token, device_id

    def post(self, path, value):
        req = urllib.request.Request(self.base+path, data=json.dumps(value).encode(), headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise PermissionError('This computer was unpaired.') from None
            try: message = json.load(error)['error']
            except Exception: message = 'Connection unavailable.'
            raise ValueError(message) from None

    def claim(self, code, os_name, name):
        value = self.post('/claim', {'code':code,'os':os_name,'name':name})
        self.token, self.device_id = value['token'], value['device_id']
        return value

    def save(self, path):
        path = Path(path);path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as file:
            json.dump({'base':self.base,'token':self.token,'device_id':self.device_id},file)
        os.chmod(temporary,0o600);temporary.replace(path)

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text()))
