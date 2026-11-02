import sys,time,unittest,uuid,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from task_execution import execute
class DesktopDispatchTests(unittest.TestCase):
 def setUp(self):
  self.calls=[];self.platform=SimpleNamespace(open_app=lambda b:self.calls.append(b) or True)
  self.id=str(uuid.uuid4());self.state={'allowed_apps':[{'id':self.id,'name':'Calculator','bundle':'com.apple.calculator'}]}
 def run_task(self,tool,**args):return execute({'task_id':'t','call_id':'c','tool':tool,'expires_at':str(int(time.time()*1000)+60000),**args},self.state,self.platform)
 def test_only_approved_unexpired_apps(self):
  self.assertEqual(self.run_task('open_app',app='Notes')['status'],'failed')
  self.assertEqual(self.run_task('open_app',app_id=self.id,expires_at='0')['status'],'failed')
  self.assertFalse(self.calls)
  self.assertEqual(self.run_task('open_app',app='Calculator',expires_at=str(int(time.time()*1000)+60000))['status'],'succeeded')
  self.assertEqual(self.calls,['com.apple.calculator'])
 def test_open_app_matches_real_names_by_alias(self):
  import uuid as _uuid
  self.state['allowed_apps'].append({'id':str(_uuid.uuid4()),'name':'Google Chrome','bundle':'com.google.Chrome'})
  self.state['allowed_apps'].append({'id':str(_uuid.uuid4()),'name':'Finder','bundle':'com.apple.finder'})
  self.assertEqual(self.run_task('open_app',app='chrome')['status'],'succeeded')
  self.assertEqual(self.run_task('open_app',app='files')['status'],'succeeded')
  self.assertEqual(self.calls,['com.google.Chrome','com.apple.finder'])
  self.assertEqual(self.run_task('open_app',app='safari')['status'],'failed')
 def test_phone_approval_skips_computer_approval(self):
  from unittest import mock as _mock
  def boom(review):raise AssertionError('computer approval must not run')
  client=SimpleNamespace(post=lambda path,body:{'phone_approved':True} if path=='/agent/start' else {})
  payload={'task_id':'t','call_id':'c','tool':'open_website','url':'https://example.com/x','expires_at':str(int(time.time()*1000)+60000)}
  with _mock.patch('webbrowser.open') as opened:
   out=execute(payload,self.state,self.platform,client=client,approve=boom)
  self.assertEqual(out['status'],'succeeded')
  opened.assert_called_once_with('https://example.com/x')
 def test_connected_file_tools_run_with_write_grant(self):
  import json as _json
  from pypdf import PdfWriter as _Writer
  with tempfile.TemporaryDirectory() as d:
   Path(d,'note.txt').write_text('hello')
   first,second=Path(d,'a.pdf'),Path(d,'b.pdf')
   for target in (first,second):
    writer=_Writer();writer.add_blank_page(72,72)
    with target.open('wb') as stream:writer.write(stream)
   self.state['grants']=[{'path':str(Path(d).resolve()),'access':'write'}]
   approve=lambda review:True
   base={'task_id':'t','call_id':'c','expires_at':str(int(time.time()*1000)+60000)}
   out=execute({**base,'tool':'convert_file','path':'a.pdf','to':'txt'},self.state,self.platform,approve=approve)
   self.assertEqual(out['status'],'succeeded')
   self.assertTrue(Path(d,'a.txt').exists())
   out=execute({**base,'tool':'pdf_pages','action':'merge','paths_json':_json.dumps(['a.pdf','b.pdf'])},self.state,self.platform,approve=approve)
   self.assertEqual(out['status'],'succeeded')
   out=execute({**base,'tool':'delete_files','path':'note.txt','confirm':'DELETE'},self.state,self.platform,approve=approve)
   self.assertEqual(out['error_code'],'permission_denied')
   self.state['grants']=[{'path':str(Path(d).resolve()),'access':'delete'}]
   out=execute({**base,'tool':'delete_files','path':'note.txt','confirm':'DELETE'},self.state,self.platform,approve=approve)
   self.assertEqual(out['status'],'succeeded')
   out=execute({**base,'tool':'restore_deleted','name':'note.txt'},self.state,self.platform,approve=approve)
   self.assertEqual(out['status'],'succeeded')
   self.assertTrue(Path(d,'note.txt').exists())
 def test_open_asks_one_time_folder_grant(self):
  import task_execution as _te
  from unittest import mock as _mock
  import handlers as _handlers
  with tempfile.TemporaryDirectory() as d:
   Path(d,'brief.txt').write_text('hello')
   _te.DEFAULT_GRANT_DIR = d
   self.addCleanup(setattr, _te, 'DEFAULT_GRANT_DIR', None)
   self.state['grants'] = []
   asked = []
   def approve(review):
    asked.append(review)
    return True
   base={'task_id':'t','call_id':'c','expires_at':str(int(time.time()*1000)+60000)}
   out=execute({**base,'tool':'search_documents','query':'brief'},self.state,self.platform,approve=approve)
   self.assertEqual(out['status'],'succeeded')
   self.assertEqual(len(self.state['grants']),1)
   self.assertEqual(self.state['grants'][0]['access'],'read')
   self.assertTrue(out.get('grant_added'))
   self.assertEqual(asked[0]['tool'],'grant_folder')
   with _mock.patch.object(_handlers,'default_open_file') as opened:
    out=execute({**base,'tool':'open_document','query':'brief'},self.state,self.platform,approve=approve)
   self.assertEqual(out['status'],'succeeded')
   self.assertEqual(len(opened.call_args_list),1)
 def test_denied_grant_keeps_permission_error(self):
  import task_execution as _te
  with tempfile.TemporaryDirectory() as d:
   _te.DEFAULT_GRANT_DIR = d
   self.addCleanup(setattr, _te, 'DEFAULT_GRANT_DIR', None)
   self.state['grants'] = []
   base={'task_id':'t','call_id':'c','expires_at':str(int(time.time()*1000)+60000)}
   out=execute({**base,'tool':'search_documents','query':'brief'},self.state,self.platform,approve=lambda review:False)
   self.assertEqual(out['error_code'],'permission_denied')
   self.assertIn('Approve the folder request on your computer',out['message'])
   self.assertEqual(self.state['grants'],[])
   out=execute({**base,'tool':'search_documents','query':'brief'},self.state,self.platform,approve=None)
   self.assertEqual(out['error_code'],'permission_denied')
   self.assertIn('Choose a folder in the computer permissions first.',out['message'])
 def test_no_remote_process_or_writes(self):
  for tool in ['process_run','fs_write','organize_photos','fetch_upload','transfer_selected_file']:
   self.assertEqual(self.run_task(tool)['error_code'],'permission_denied')
 def test_reads_require_granted_folder(self):
  self.assertEqual(self.run_task('fs_list')['status'],'failed')
  with tempfile.TemporaryDirectory() as d:
   Path(d,'brief.txt').write_text('hello')
   self.state['grants']=[{'path':str(Path(d).resolve()),'access':'read'}]
   self.assertEqual(self.run_task('fs_read',path='brief.txt')['status'],'succeeded')
   self.assertEqual(self.run_task('fs_read',path='../outside')['status'],'failed')
 def test_new_writes_need_approval_and_delete_rank(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'old.txt').write_text('keep')
   self.state['grants']=[{'path':str(Path(d).resolve()),'access':'write'}]
   base={'task_id':'t','call_id':'c','expires_at':str(int(time.time()*1000)+60000)}
   out=execute({**base,'tool':'rename_file','path':'old.txt','new_name':'new.txt'},self.state,self.platform,approve=lambda review:False)
   self.assertEqual(out['error_code'],'permission_denied')
   self.assertTrue(Path(d,'old.txt').exists())
   out=execute({**base,'tool':'rename_file','path':'old.txt','new_name':'new.txt'},self.state,self.platform,approve=lambda review:True)
   self.assertEqual(out['status'],'succeeded')
   self.assertEqual(Path(d,'new.txt').read_text(),'keep')
   out=execute({**base,'tool':'undo_edit','path':'new.txt'},self.state,self.platform,approve=lambda review:True)
   self.assertEqual(out['error_code'],'no_match')
   out=execute({**base,'tool':'search_contents','query':'keep'},self.state,self.platform,approve=None)
   self.assertEqual(out['status'],'succeeded')
   out=execute({**base,'tool':'empty_trash','confirm':'EMPTY'},self.state,self.platform,approve=lambda review:True)
   self.assertEqual(out['error_code'],'permission_denied')
   self.state['grants']=[{'path':str(Path(d).resolve()),'access':'delete'}]
   out=execute({**base,'tool':'empty_trash','confirm':'EMPTY'},self.state,self.platform,approve=lambda review:True)
   self.assertEqual(out['status'],'succeeded')
