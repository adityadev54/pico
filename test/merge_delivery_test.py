"""Synthetic merge regressions. No provider calls or user files."""
import json,sys,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from agent_server import make_handler
from companion import Companion

class LocalServerAuthTests(unittest.TestCase):
 def test_empty_token_fails_closed(self):
  with self.assertRaises(ValueError):make_handler('',[])
 def test_http_rejects_missing_token_and_browser_origin(self):
  from http.server import ThreadingHTTPServer
  server=ThreadingHTTPServer(('127.0.0.1',0),make_handler('synthetic-token',[]));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   url='http://127.0.0.1:'+str(server.server_port)+'/execute'
   for headers in ({},{'Authorization':'Bearer wrong'},{'Authorization':'Bearer synthetic-token','Origin':'https://untrusted.example'}):
    req=urllib.request.Request(url,data=b'{}',headers={'Content-Type':'application/json',**headers})
    with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req,timeout=5)
    self.assertEqual(e.exception.code,401)
   req=urllib.request.Request(url,data=json.dumps({'tool':'fs_list','arguments':{}}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer synthetic-token'})
   with urllib.request.urlopen(req,timeout=5) as r:self.assertEqual(json.load(r)['status'],'failed')
  finally:server.shutdown();server.server_close()
class DesktopPlaceStateTests(unittest.TestCase):
 def setUp(self):
  self.c=Companion.__new__(Companion);self.c.lock=threading.RLock();self.c.acks=[];self.c.state={'places':{},'handled':[]};self.c.overlay=None;self.saved=0;self.cards=[]
  self.c.save=lambda:setattr(self,'saved',self.saved+1)
  self.c.show_card=lambda identity:self.cards.append(identity)
 def message(self,identity,kind,payload):self.c.consume({'id':identity,'kind':kind,'payload':payload})
 def test_state_arriving_before_note_is_preserved_without_replaying_a_draft(self):
  self.message('park','parked',{'place_id':'note','status':'parked'})
  self.message('place','place',{'place_id':'note','sentence':'Synthetic thought'})
  self.assertEqual(self.c.state['places']['note']['status'],'parked');self.assertFalse(self.cards)
  self.message('unpark','parked',{'place_id':'note','status':'ready'});self.assertEqual(self.cards,['note'])
  self.message('done','parked',{'place_id':'note','status':'finished'})
  self.assertEqual(self.c.state['places']['note']['status'],'finished');self.assertEqual(self.saved,4)
  self.message('done','parked',{'place_id':'note','status':'finished'});self.assertEqual(self.saved,4)
  self.message('late-ready','parked',{'place_id':'note','status':'ready'});self.assertEqual(self.c.state['places']['note']['status'],'finished')

class LateLocalConfigTests(unittest.TestCase):
 def test_proxy_uses_token_loaded_after_import(self):
  import io
  from unittest.mock import patch
  from server.agent.tools_proxy import dispatch_to_helper
  calls=[]
  def receive(request,timeout):calls.append(request);return io.BytesIO(b'{"status":"succeeded"}')
  with patch.dict('os.environ',{'PICO_AGENT_TOKEN':'late-loaded-test-token'}),patch('server.agent.tools_proxy.urllib.request.urlopen',receive):
   self.assertEqual(dispatch_to_helper({'task_id':'t'})['status'],'succeeded')
  self.assertEqual(calls[0].get_header('Authorization'),'Bearer late-loaded-test-token')
