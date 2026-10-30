"""Private, JSON-only mail objects. Stores Pico messages separately from account chat tables."""
import urllib.error
from .service import ApiError

class Mailbox:
    bucket = 'pico-mailbox'
    def __init__(self, database):
        self.database = database

    def ensure(self):
        try:
            bucket = self.database.request('/storage/v1/bucket/'+self.bucket)
            if bucket.get('public'):
                raise ValueError('Pico mailbox must be private.')
        except urllib.error.HTTPError as error:
            if error.code not in (400,404):raise
            self.database.request('/storage/v1/bucket', {'id':self.bucket,'name':self.bucket,'public':False,'file_size_limit':16000,'allowed_mime_types':['application/json']}, 'POST')

    def prefix(self, owner, device, phone):
        return f'{owner}/{device}/'+('phone' if phone else 'computer')

    def list(self, owner, device, phone=False):
        prefix=self.prefix(owner,device,phone)
        files=self.database.request('/storage/v1/object/list/'+self.bucket, {'prefix':prefix,'limit':30,'offset':0,'sortBy':{'column':'created_at','order':'asc'}}, 'POST')
        messages=[]
        for file in files:
            if file['name'].endswith('.json'):
                messages.append(self.database.request('/storage/v1/object/'+self.bucket+'/'+prefix+'/'+file['name']))
        return messages

    def put(self, owner, device, id, message, phone=False):
        path='/storage/v1/object/'+self.bucket+'/'+self.prefix(owner,device,phone)+'/'+id+'.json'
        try:self.database.request(path, {'id':id,**message}, 'POST')
        except urllib.error.HTTPError as error:
            if error.code not in (400,409):raise
            # A retry is successful only if this exact owner's mail already exists.
            current=self.database.request(path)
            if current.get('id')!=id:raise ApiError(409,'Message conflict.')

    def delete(self, owner, device, ids, phone=False):
        if ids:
            prefix=self.prefix(owner,device,phone)
            self.database.request('/storage/v1/object/'+self.bucket, {'prefixes':[prefix+'/'+id+'.json' for id in ids]}, 'DELETE')


class Uploads:
    """Owner-scoped phone-upload artifacts (B07). One immutable JSON object
    per content digest: retries dedupe by id, owners can never read across."""
    bucket = 'pico-uploads'
    def __init__(self, database):
        self.database = database

    def ensure(self):
        try:
            bucket = self.database.request('/storage/v1/bucket/'+self.bucket)
            if bucket.get('public'):
                raise ValueError('Pico uploads must be private.')
        except urllib.error.HTTPError as error:
            if error.code not in (400,404):raise
            self.database.request('/storage/v1/bucket', {'id':self.bucket,'name':self.bucket,'public':False,'file_size_limit':2000000,'allowed_mime_types':['application/json']}, 'POST')

    def put(self, owner, artifact_id, obj):
        """Store a new artifact. Returns True when it already existed."""
        path = '/storage/v1/object/'+self.bucket+f'/{owner}/{artifact_id}.json'
        try:
            self.database.request(path, {'id':artifact_id,**obj}, 'POST')
            return False
        except urllib.error.HTTPError as error:
            if error.code not in (400,409):raise
            try:
                current = self.get(owner, artifact_id)
            except urllib.error.HTTPError:
                raise error from None
            if current.get('id') != artifact_id:
                raise error from None
            return True

    def get(self, owner, artifact_id):
        return self.database.request(
            '/storage/v1/object/'+self.bucket+f'/{owner}/{artifact_id}.json')
