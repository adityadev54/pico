import io,json,os,stat,sys,tempfile,time,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from handlers import dispatch
from tools import TOOL_REGISTRY,ToolError
from native_search import NativeError
from task_execution import execute

class FileManagementTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
  self.grants=[{'path':str(self.root),'access':'delete'}]
  self.ctx={'grants':self.grants,'current_grants':lambda:self.grants}
  (self.root/'notes.txt').write_text('My lecture notes')
 def run_tool(self,kind,**args):return dispatch(kind,TOOL_REGISTRY.validate(kind,args),self.ctx)
 def test_trash_restore_and_restore_collision_preserve_bytes(self):
  before=(self.root/'notes.txt').read_bytes()
  data,_=self.run_tool('delete_files',path='notes.txt',confirm='DELETE')
  self.assertFalse((self.root/'notes.txt').exists());self.assertEqual(data['trashed_count'],1)
  (self.root/'notes.txt').write_text('newer notes')
  result,_=self.run_tool('restore_deleted',name='notes.txt')
  self.assertEqual((self.root/'notes.txt').read_text(),'newer notes');self.assertEqual((self.root/result['path']).read_bytes(),before)
 def test_write_grant_cannot_trash_and_revocation_stops_operation(self):
  self.grants[0]['access']='write'
  with self.assertRaises(NativeError):self.run_tool('delete_files',path='notes.txt',confirm='DELETE')
  self.grants[0]['access']='delete';self.ctx['current_grants']=lambda:[]
  with self.assertRaises(NativeError):self.run_tool('delete_files',path='notes.txt',confirm='DELETE')
  self.assertTrue((self.root/'notes.txt').exists())
 def test_permanent_empty_requires_extra_local_approval(self):
  self.run_tool('delete_files',path='notes.txt',confirm='DELETE')
  payload={'task_id':'test','call_id':'c','tool':'empty_trash','confirm':'EMPTY','expires_at':str(int(time.time()*1000)+60000)}
  client=SimpleNamespace(post=lambda *a:{'phone_approved':True})
  asked=[]
  result=execute(payload,{'grants':self.grants},SimpleNamespace(),client=client,approve=lambda review:asked.append(review) or False)
  self.assertEqual(result['status'],'failed');self.assertEqual(len(asked),1)
  self.assertTrue(list((self.root/'.pico-trash').glob('*.data')))
  result=execute(payload,{'grants':self.grants},SimpleNamespace(),client=client,approve=lambda _:True)
  self.assertEqual(result['status'],'succeeded');self.assertFalse(list((self.root/'.pico-trash').glob('*.data')))
 def test_zip_round_trip_and_originals_stay_untouched(self):
  before=(self.root/'notes.txt').read_bytes()
  result,_=self.run_tool('archive',action='create',paths_json='["notes.txt"]')
  self.assertEqual(zipfile.ZipFile(self.root/result['path']).read('notes.txt'),before)
  extracted,_=self.run_tool('archive',action='extract',paths_json=json.dumps([result['path']]))
  self.assertEqual((self.root/extracted['output']/'notes.txt').read_bytes(),before)
  self.assertEqual((self.root/'notes.txt').read_bytes(),before)
 def test_zip_rejects_escaping_hidden_and_symlink_entries_before_creating_outputs(self):
  for name in ('../escape','/absolute','folder/../../escape','folder\\escape','.hidden/secret'):
   with zipfile.ZipFile(self.root/'unsafe.zip','w') as z:z.writestr(name,'x')
   with self.assertRaises((ToolError,NativeError)):self.run_tool('archive',action='extract',paths_json='["unsafe.zip"]')
   self.assertFalse((self.root/'unsafe-extracted').exists())
  with zipfile.ZipFile(self.root/'unsafe.zip','w') as z:
   member=zipfile.ZipInfo('link');member.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(member,'/tmp')
  with self.assertRaises(ToolError):self.run_tool('archive',action='extract',paths_json='["unsafe.zip"]')
 def test_zip_bomb_limit_and_unapproved_roots(self):
  with zipfile.ZipFile(self.root/'large.zip','w',zipfile.ZIP_DEFLATED) as z:z.writestr('large.txt',b'0'*(11*1024*1024))
  with self.assertRaises(ToolError):self.run_tool('archive',action='extract',paths_json='["large.zip"]')
  self.ctx['grants']=[]
  with self.assertRaises(NativeError):self.run_tool('archive',action='create',paths_json='["notes.txt"]')
 def test_links_cannot_delete_outside_file(self):
  with tempfile.TemporaryDirectory() as outside:
   target=Path(outside)/'private.txt';target.write_text('keep')
   (self.root/'link.txt').symlink_to(target)
   with self.assertRaises((ToolError,NativeError)):self.run_tool('delete_files',path='link.txt',confirm='DELETE')
   self.assertEqual(target.read_text(),'keep')
 def test_missing_grant_asks_once_and_resumes_only_with_explicit_choice(self):
  state={'grants':[]};asked=[]
  def allow(access):
   asked.append(access);g={'path':str(self.root),'access':access};state['grants']=[g];return g
  payload={'task_id':'test','call_id':'c','tool':'search_documents','query':'notes','expires_at':str(int(time.time()*1000)+60000)}
  result=execute(payload,state,SimpleNamespace(),request_grant=allow)
  self.assertEqual(result['status'],'succeeded');self.assertEqual(asked,['read'])
  result=execute(payload,{'grants':[]},SimpleNamespace(),request_grant=lambda _:None)
  self.assertEqual(result['error_code'],'permission_denied')
