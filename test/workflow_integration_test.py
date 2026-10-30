"""Real local HTTP workflow tests. Synthetic files; never a paid provider call."""
import base64,hashlib,json,sys,tempfile,threading,time,unittest,uuid,urllib.request,urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from task_execution import execute,grant_id
from client import DeviceClient
from relay.app import make_handler
from relay.service import PicoService,ApiError
from relay.state import RelayState
from relay.tests.fake import FakeSupabase
from relay.workflows import create,approve

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.folder=self.root/'files';self.folder.mkdir()
  self.db=FakeSupabase();self.service=PicoService(self.db,RelayState(self.root/'relay.sqlite'))
  self.http=__import__('http.server',fromlist=['ThreadingHTTPServer']).ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.service));threading.Thread(target=self.http.serve_forever,daemon=True).start()
  self.addCleanup(self.http.server_close);self.addCleanup(self.http.shutdown)
  self.base=f'http://127.0.0.1:{self.http.server_port}';code=self.post('/pairing',{})['code']
  paired=self.post('/claim',{'code':code,'name':'Workflow test','os':'macos'},token='')
  self.device=paired['device_id'];self.client=DeviceClient(self.base,paired['token'],self.device)
  self.state={'grants':[{'path':str(self.folder),'access':'write'}]}
 def post(self,path,body,token='phone'):
  req=urllib.request.Request(self.base+path,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
 def task(self,kind,input,confirmed=False):return self.post('/tasks',{'device_id':self.device,'kind':kind,'input':input,'confirmed':confirmed})
 def row(self,task):
  from relay.task_records import view
  return view(self.db.db('tasks',{'id':'eq.'+task['id']})[0])
 def run_task(self,task,approve_action=lambda _:True):
  mail=next(m for m in self.client.post('/agent/poll',{})['mail'] if m['payload'].get('task_id')==task['id'])
  result=execute(mail['payload'],self.state,SimpleNamespace(),client=self.client,approve=approve_action)
  self.client.post('/agent/mail',{'kind':'tool_result','payload':result});self.client.post('/agent/ack',{'ids':[mail['id']]})
  return self.row(task)
 def test_find_read_send_receive_exact_bytes(self):
  raw=b'Launch checklist: install, pair, verify.';(self.folder/'brief.txt').write_bytes(raw)
  search=self.run_task(self.task('find_document',{'query':'brief.txt'}));candidate=search['result']['candidates'][0]
  self.assertEqual(search['status'],'awaiting_approval')
  selected={'search_task_id':search['id'],'candidate_id':candidate['candidate_id']}
  read=self.run_task(self.task('read_document',selected));self.assertEqual(read['result']['excerpt'],raw.decode())
  transfer=self.run_task(self.task('send_file',selected));self.assertEqual(transfer['status'],'verifying')
  response=self.post('/files/download',{'id':transfer['id']});received=base64.b64decode(response['content_base64']);self.assertEqual(received,raw)
  self.post('/tasks/receipt',{'task_id':transfer['id'],'size_bytes':len(received),'digest':hashlib.sha256(received).hexdigest()})
  self.assertEqual(self.row(transfer)['result']['receipt'],'verified')
  self.db.auth_user='other-owner'
  with self.assertRaises(urllib.error.HTTPError) as denial:self.post('/files/download',{'id':transfer['id']})
  self.assertEqual(denial.exception.code,404)
 def test_changed_file_and_forged_candidate_never_transfer(self):
  f=self.folder/'brief.txt';f.write_text('original')
  search=self.run_task(self.task('find_document',{'query':'brief'}));selected={'search_task_id':search['id'],'candidate_id':search['result']['candidates'][0]['candidate_id']}
  with self.assertRaises(urllib.error.HTTPError):self.task('send_file',{**selected,'candidate_id':str(uuid.uuid4())})
  task=self.task('send_file',selected);f.write_text('changed')
  result=self.run_task(task);self.assertEqual(result['status'],'failed');self.assertEqual(result['result']['error_code'],'candidate_changed')
 def test_phone_review_runs_file_write_without_duplicate_desktop_review(self):
  input={'name':'note.txt','text':'hello','grant_id':grant_id(self.folder)}
  with self.assertRaises(urllib.error.HTTPError):self.task('create_note',input)
  saved=self.run_task(self.task('create_note',input,True),lambda _:self.fail('Phone-approved file must not prompt on desktop'));self.assertEqual(saved['status'],'completed');self.assertEqual((self.folder/'note.txt').read_text(),'hello')
  old=saved['result']['digest'];(self.folder/'note.txt').write_text('user revision')
  edited=self.run_task(self.task('edit_file',{'name':'note.txt','text':'overwrite','base_revision':old},True))
  self.assertEqual(edited['status'],'failed');self.assertEqual((self.folder/'note.txt').read_text(),'user revision')
 def test_phone_upload_verified_and_no_overwrite(self):
  response=self.post('/uploads',{'device_id':self.device,'name':'phone.txt','content_base64':base64.b64encode(b'from phone').decode(),'purpose':'transfer','grant_id':grant_id(self.folder)})
  task={'id':response['task_id']};done=self.run_task(task);self.assertEqual(done['status'],'completed');self.assertEqual((self.folder/'phone.txt').read_bytes(),b'from phone')
 def test_photo_copy_preserves_originals(self):
  (self.folder/'a.jpg').write_bytes(b'image one');(self.folder/'b.png').write_bytes(b'image one');(self.folder/'c.jpg').write_bytes(b'image two')
  done=self.run_task(self.task('organize_photos',{'folder':'ReviewPhotos'},True))
  self.assertEqual(done['status'],'completed');self.assertEqual(done['result']['copied_count'],2);self.assertEqual(done['result']['duplicates_skipped'],1);self.assertEqual((self.folder/'a.jpg').read_bytes(),b'image one')
 def test_proposal_never_runs_before_approval_and_cancel_wins(self):
  task=create(self.service,'owner-1',self.device,'','create_note',{'name':'draft.txt','text':'draft'},proposal=True)
  self.assertEqual(self.client.post('/agent/poll',{})['mail'],[])
  self.post('/tasks/approve',{'id':task['id'],'confirmed':True,'grant_id':grant_id(self.folder)})
  done=self.run_task(task);self.assertEqual(done['status'],'completed')
  with self.assertRaises(urllib.error.HTTPError):self.post('/tasks/approve',{'id':task['id'],'confirmed':True})
  second=self.task('create_note',{'name':'cancel.txt','text':'no'},True);self.post('/tasks/cancel',{'id':second['id']})
  self.assertFalse(any(m['kind']=='tool_call' and m['payload']['task_id']==second['id'] for m in self.client.post('/agent/poll',{})['mail']))
 def test_durable_outbox_recovers_same_call_id(self):
  original=self.service.enqueue
  with patch.object(self.service,'enqueue',side_effect=OSError('offline')):task=self.task('find_document',{'query':'x'})
  pending=self.service.jobs.pending('owner-1',self.device);self.assertEqual(len(pending),1);identity=pending[0]['call_id']
  restored=PicoService(self.db,RelayState(self.root/'relay.sqlite'));messages=restored.mailbox('owner-1',self.device)
  self.assertEqual(messages[0]['payload']['call_id'],identity);self.assertEqual(len(restored.mailbox('owner-1',self.device)),1)
 def test_command_approval_and_secret_environment(self):
  command=[sys.executable,'-c','import os;print(os.getenv("MUSE_API_KEY","absent"))']
  with patch.dict('os.environ',{'MUSE_API_KEY':'private-test-value'}):done=self.run_task(self.task('run_command',{'argv':command},True))
  self.assertEqual(done['status'],'completed');self.assertIn('absent',done['result']['stdout']);self.assertNotIn('private-test-value',done['result']['stdout'])
 def test_summary_and_status_deny_other_accounts_without_provider_call(self):
  with patch('urllib.request.urlopen',side_effect=AssertionError('provider must not be called')):
   with patch.dict('os.environ',{'PICO_MODEL_OWNER_IDS':'allowed-owner'}):
    from relay.model_status import status
    self.assertEqual(status('other-owner')['state'],'restricted')
    from relay.model_summary import summarize
    with self.assertRaises(ApiError) as error:summarize(self.service,'other-owner',{'id':str(uuid.uuid4()),'confirmed':True})
    self.assertEqual(error.exception.status,403)

 def test_summary_is_explicit_bounded_and_uses_one_request(self):
  import io
  (self.folder/'long.txt').write_text('Selected excerpt. '*200)
  task=self.run_task(self.task('read_file',{'path':'long.txt'}))
  from relay.model_summary import summarize
  captured=[]
  class Response(io.BytesIO):
   def __enter__(self):return self
   def __exit__(self,*args):self.close()
  def authorize(request,task,cfg):captured.append(json.loads(request.data))
  def provider(request,**kwargs):return Response(json.dumps({'choices':[{'message':{'content':'A concise synthetic summary.'}}]}).encode())
  config={'url':'https://api.meta.ai/v1/chat/completions','key':'test-only','model':'muse-spark-1.3'}
  with patch.dict('os.environ',{'PICO_MODEL_OWNER_IDS':'owner-1'}),patch('relay.model_summary.muse_config',return_value=config),patch('relay.model_summary.authorize',side_effect=authorize),patch('relay.model_summary.urllib.request.urlopen',side_effect=provider):
   with self.assertRaises(ApiError):summarize(self.service,'owner-1',{'id':task['id'],'request_id':str(uuid.uuid4())})
   self.assertEqual(captured,[])
   out=summarize(self.service,'owner-1',{'id':task['id'],'request_id':str(uuid.uuid4()),'confirmed':True})
  self.assertEqual(len(captured),1);self.assertLessEqual(len(captured[0]['messages'][1]['content']),1500);self.assertEqual(captured[0]['max_completion_tokens'],400);self.assertEqual(out['summary'],'A concise synthetic summary.')
 def test_interrupted_task_is_reported_once_without_reexecution(self):
  from companion import Companion
  c=Companion.__new__(Companion);c.lock=threading.RLock();c.state_file=self.root/'helper.json'
  c.state={'outgoing':[],'handled':[],'task_journal':{'mail-1':{'status':'running','payload':{'task_id':str(uuid.uuid4()),'call_id':str(uuid.uuid4())}}}}
  c.recover_tasks();c.recover_tasks()
  self.assertEqual(len(c.state['outgoing']),1);self.assertEqual(c.state['outgoing'][0]['payload']['error_code'],'interrupted')
  self.assertEqual(json.loads(c.state_file.read_text())['handled'],['mail-1'])
 def test_running_command_can_be_cancelled_through_mailbox(self):
  from companion import Companion
  command=self.task('run_command',{'argv':[sys.executable,'-c','import time;time.sleep(5)']},True)
  message=next(m for m in self.client.post('/agent/poll',{})['mail'] if m['kind']=='tool_call')
  c=Companion.__new__(Companion);c.lock=threading.RLock();c.events=__import__('queue').Queue();c.acks=[];c.client=self.client;c.platform=SimpleNamespace();c.state_file=self.root/'helper-cancel.json';c.running_tasks={};c.cancelled_tasks=set()
  c.state={**self.state,'outgoing':[],'handled':[],'task_journal':{}};c.approve_task=lambda review:True
  worker=threading.Thread(target=c.consume,args=(message,),daemon=True);worker.start()
  until=time.monotonic()+3
  while command['id'] not in c.running_tasks and time.monotonic()<until:time.sleep(.01)
  self.assertIn(command['id'],c.running_tasks)
  self.post('/tasks/cancel',{'id':command['id']})
  cancellation=next(m for m in self.client.post('/agent/poll',{})['mail'] if m['kind']=='cancel');c.consume(cancellation)
  worker.join(3);self.assertFalse(worker.is_alive())
  for result in c.state['outgoing']:self.client.post('/agent/mail',result)
  self.assertEqual(self.row(command)['status'],'cancelled')

 def test_deleted_task_result_does_not_block_future_outbox(self):
  from companion import Companion
  from client import DeviceError
  c=Companion.__new__(Companion)
  gone=SimpleNamespace(post=lambda *a:(_ for _ in ()).throw(DeviceError('Request not found.',404)))
  c.deliver_message(gone,{'kind':'tool_result'})
  transient=SimpleNamespace(post=lambda *a:(_ for _ in ()).throw(DeviceError('Temporary outage',503)))
  with self.assertRaises(DeviceError):c.deliver_message(transient,{'kind':'tool_result'})

 def test_existing_kind_constraint_uses_owned_metadata_without_schema_change(self):
  import io
  original=self.db.db
  def constrained(table,filters=None,body=None,method='GET'):
   if table=='tasks' and method=='POST' and body.get('kind') not in ('open_app','find_document','send_file'):
    raise urllib.error.HTTPError('fake',400,'constraint',{},io.BytesIO(json.dumps({'code':'23514','message':'tasks_kind_check'}).encode()))
   return original(table,filters,body,method)
  with patch.object(self.db,'db',side_effect=constrained):
   task=self.task('create_note',{'name':'compatible.txt','text':'compatible'},True)
   self.assertEqual(task['kind'],'create_note');self.assertEqual(original('tasks',{'id':'eq.'+task['id']})[0]['kind'],'open_app')
   done=self.run_task(task);self.assertEqual(done['status'],'completed');self.assertEqual((self.folder/'compatible.txt').read_text(),'compatible')
   proposal=create(self.service,'owner-1',self.device,'','create_note',{'name':'proposal.txt','text':'review'},proposal=True)
   self.post('/tasks/approve',{'id':proposal['id'],'confirmed':True,'grant_id':grant_id(self.folder)})
   done=self.run_task(proposal);self.assertEqual(done['status'],'completed');self.assertEqual((self.folder/'proposal.txt').read_text(),'review')

 def test_muse_draft_becomes_reviewed_task_without_auto_execution(self):
  self.client.post('/agent/poll',{'capabilities':{'workflow_version':2,'workspaces':[{'id':grant_id(self.folder),'name':'files','access':'write'}]}})
  with patch.dict('os.environ',{'PICO_MODEL_ENABLED':'1','PICO_MODEL_OWNER_IDS':'owner-1'}),patch('server.agent.planner.plan',return_value={'tool_call':{'tool':'fs_write','arguments':{'path':'checklist.txt','content':'1. Install\n2. Pair\n3. Verify'}}}) as planner:
   response=self.post('/ai/request',{'device_id':self.device,'request_id':str(uuid.uuid4()),'text':'Draft a three-item launch checklist into checklist.txt.'})
  self.assertEqual(planner.call_count,1);task=response['task'];self.assertEqual(task['kind'],'create_note');self.assertEqual(task['status'],'awaiting_approval');self.assertFalse((self.folder/'checklist.txt').exists())
  self.assertFalse(any(m['kind']=='tool_call' for m in self.client.post('/agent/poll',{})['mail']))
  self.post('/tasks/approve',{'id':task['id'],'confirmed':True,'grant_id':grant_id(self.folder)})
  done=self.run_task(task);self.assertEqual(done['status'],'completed');self.assertIn('Pair',(self.folder/'checklist.txt').read_text())

class PhoneApprovalTests(unittest.TestCase):
 setUp=WorkflowTests.setUp
 post=WorkflowTests.post
 task=WorkflowTests.task
 row=WorkflowTests.row
 run_task=WorkflowTests.run_task
 def test_unreviewed_proposal_cannot_forge_phone_approval(self):
  task=create(self.service,'owner-1',self.device,'','create_note',{'name':'forged.txt','text':'not approved','_pico_phone_approved':True},proposal=True)
  self.assertNotIn('_pico_phone_approved',task['input'])
  self.assertFalse(self.client.post('/agent/start',{'task_id':task['id']})['phone_approved'])
 def test_phone_approval_does_not_replace_a_write_grant(self):
  self.state['grants'][0]['access']='read'
  result=self.run_task(self.task('create_note',{'name':'denied.txt','text':'no access'},True),lambda _:self.fail('No desktop prompt expected'))
  self.assertEqual(result['status'],'failed');self.assertFalse((self.folder/'denied.txt').exists())
