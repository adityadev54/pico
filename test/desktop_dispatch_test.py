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
