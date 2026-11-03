"""Authenticated loopback relay tests; no actual cloud or model calls."""
import json,sys,tempfile,threading,time,unittest,uuid,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from relay.app import make_handler
from relay.service import PicoService
from relay.state import RelayState
from relay.tests.fake import FakeSupabase
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from client import DeviceClient

class RoutineRelayTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.db=FakeSupabase();self.service=PicoService(self.db,RelayState(Path(self.tmp.name)/'state.sqlite'))
  self.http=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.service));threading.Thread(target=self.http.serve_forever,daemon=True).start();self.addCleanup(self.http.server_close);self.addCleanup(self.http.shutdown)
  self.base=f'http://127.0.0.1:{self.http.server_port}'
  code=self.post('/pairing',{})['code'];p=self.post('/claim',{'code':code,'name':'Teach test','os':'macos'})
  self.device=p['device_id'];self.client=DeviceClient(self.base,p['token'],self.device)
 def post(self,path,body):
  request=urllib.request.Request(self.base+path,data=json.dumps(body).encode(),headers={'Authorization':'Bearer phone','Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=10) as r:return json.load(r)
 def request(self,**overrides):
  p={'query':'run:'+str(uuid.uuid4()),'request_id':str(uuid.uuid4()),'expires_at':str(int(time.time()*1000)+60000)};p.update(overrides)
  return self.post('/mail',{'device_id':self.device,'kind':'skill_request','payload':p}),p
 def test_queue_device_model_and_result(self):
  queued,p=self.request();mail=self.client.post('/agent/poll',{})['mail'];self.assertEqual(mail[0]['payload'],p)
  with patch('server.skills.model.complete',return_value={'instructions':'Two ideas'}) as model:
   result=self.client.post('/agent/skills/model',{'operation':'learn'})
   self.assertEqual(result,{'instructions':'Two ideas'});self.assertEqual(model.call_args.args[0],'owner-1')
  self.client.post('/agent/mail',{'kind':'skill_result','payload':{'request_id':p['request_id'],'status':'completed','message':'Saved study pack','catalog':'[]'}})
  self.assertEqual(self.service.mailbox('owner-1',self.device,True)[0]['payload']['status'],'completed')
 def test_other_owner_and_revoked_device(self):
  self.db.auth_user='other-owner'
  with self.assertRaises(urllib.error.HTTPError) as e:self.request()
  self.assertEqual(e.exception.code,404)
  self.db.auth_user='owner-1';self.post('/unpair',{'device_id':self.device})
  with patch('server.skills.model.complete') as model:
   with self.assertRaises(PermissionError):self.client.post('/agent/skills/model',{})
   model.assert_not_called()
 def test_expiry_arbitrary_commands_and_sources_blocked(self):
  for values in [{'expires_at':'0'},{'query':'shell:rm'},{'query':'run:bogus'},{'content':'private notes'}]:
   with self.assertRaises(urllib.error.HTTPError):self.request(**values)
 def test_mail_namespace_cannot_mix_with_published_app(self):
  from relay.mailbox import Mailbox
  m=Mailbox(self.db);base=m.prefix('owner','device',False)
  with patch.dict('os.environ',{'PICO_MAIL_NAMESPACE':'teach-v1'}):self.assertNotEqual(base,m.prefix('owner','device',False))

if __name__=='__main__':unittest.main()
