"""Real HTTP queue -> packaged consume method -> result, with no cloud/model traffic."""
import json,sys,tempfile,threading,time,unittest,uuid,urllib.request
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from http.server import ThreadingHTTPServer
from companion import Companion
from relay.app import make_handler
from relay.service import PicoService
from relay.state import RelayState
from relay.tests.fake import FakeSupabase
class TaskIntegrationTests(unittest.TestCase):
 def test_actual_companion_executes_before_ack(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=FakeSupabase();service=PicoService(db,RelayState(Path(tmp)/'relay.sqlite'))
   http=ThreadingHTTPServer(('127.0.0.1',0),make_handler(service));threading.Thread(target=http.serve_forever,daemon=True).start()
   try:
    base=f'http://127.0.0.1:{http.server_port}'
    def call(path,body,token):
     req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
     with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
    code=call('/pairing',{},'phone')['code'];device=call('/claim',{'code':code,'os':'macos','name':'Task test'},'')
    task=call('/tasks',{'device_id':device['device_id'],'kind':'open_app','input':{'app':'Calculator'}},'phone')
    mail=call('/agent/poll',{},device['token'])['mail'][0]
    c=Companion.__new__(Companion);c.lock=threading.RLock();c.acks=[];c.events=__import__('queue').Queue()
    c.client=SimpleNamespace(device_id=device['device_id']);c.state={'handled':[],'outgoing':[],'allowed_apps':[{'id':str(uuid.uuid4()),'name':'Calculator','bundle':'com.apple.calculator'}]}
    launches=[];persisted=[];c.platform=SimpleNamespace(open_app=lambda app:launches.append(app) or True)
    c.save=lambda:persisted.append(json.loads(json.dumps(c.state)))
    c.consume(mail)
    self.assertEqual(launches,['com.apple.calculator']);self.assertTrue(any(p['outgoing'] for p in persisted))
    self.assertEqual(c.acks,[mail['id']])
    call('/agent/mail',c.state['outgoing'][0],device['token'])
    self.assertEqual(db.tables['tasks'][0]['status'],'completed')
    c.consume(mail);self.assertEqual(len(launches),1)
    # A task requiring process/write permissions never reaches an executor.
    bad={'id':str(uuid.uuid4()),'kind':'tool_call','payload':{'task_id':task['id'],'call_id':str(uuid.uuid4()),'tool':'process_run','argv_json':'["echo","unsafe"]','expires_at':str(int(time.time()*1000)+60000)}}
    c.consume(bad);self.assertEqual(c.state['outgoing'][-1]['payload']['error_code'],'permission_denied')
   finally:http.shutdown();http.server_close()
