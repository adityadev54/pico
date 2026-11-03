"""Exercise the actual stdio adapter with temporary grants and a fake model."""
import json,os,subprocess,sys,tempfile,unittest,uuid
from pathlib import Path
AGENTS=Path(__file__).resolve().parents[1]
class WindowsWorkerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
  self.grants=[{'id':'test','path':str(self.root),'access':'delete'}];self.calls=[]
  self.worker=subprocess.Popen([sys.executable,'-u',str(AGENTS/'windows_worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(self.stop)
 def stop(self):
  self.worker.terminate();self.worker.communicate(timeout=5)
 def call(self,operation,**args):
  self.worker.stdin.write(json.dumps({'operation':operation,'directory':str(self.root/'recipes'),**args})+'\n');self.worker.stdin.flush()
  while True:
   line=self.worker.stdout.readline();self.assertTrue(line,'Worker stopped unexpectedly')
   value=json.loads(line)
   if 'callback' not in value:return value
   kind=value['callback'];self.calls.append(kind)
   if kind=='grants':reply=self.grants
   elif kind=='cancelled':reply=False
   elif kind=='model':
    if value['body']['operation']=='learn':reply={'instructions':'Make a concise cited review.'}
    else:reply={'title':'Review','ideas':[{'text':'Gravity attracts masses.','source':'S1','quote':'Gravity attracts masses.'} for _ in range(2)],'questions':[{'question':'What attracts masses?','answer':'Gravity','source':'S1','quote':'Gravity attracts masses.'} for _ in range(2)]}
   else:self.fail(kind)
   self.worker.stdin.write(json.dumps({'result':reply})+'\n');self.worker.stdin.flush()
 def tool(self,tool,**args):return self.call('tool',payload={'tool':tool,'grant_id':'test',**args})
 def test_archive_trash_restore_round_trip(self):
  (self.root/'notes.txt').write_text('real lecture')
  result=self.tool('archive',action='create',paths_json='["notes.txt"]');self.assertIn('result',result)
  self.assertTrue((self.root/result['result']['data']['path']).is_file())
  self.assertIn('result',self.tool('delete_files',path='notes.txt',confirm='DELETE'));self.assertFalse((self.root/'notes.txt').exists())
  self.assertIn('result',self.tool('restore_deleted',name='notes.txt'));self.assertEqual((self.root/'notes.txt').read_text(),'real lecture')
 def test_revoked_and_read_only_grants_stop_writes(self):
  (self.root/'notes.txt').write_text('keep me');self.grants[0]['access']='read'
  self.assertIn('error',self.tool('delete_files',path='notes.txt',confirm='DELETE'))
  self.grants=[];self.assertIn('error',self.tool('archive',action='create',paths_json='["notes.txt"]'))
  self.assertTrue((self.root/'notes.txt').exists())
 def test_real_teach_repeat_and_replay_rejection(self):
  (self.root/'notes.txt').write_text('Gravity attracts masses. 学习',encoding='utf-8')
  start=self.call('start',root=str(self.root),sources=['notes.txt'],output='example.md')['result']
  (self.root/'example.md').write_text('# Review\nGravity attracts masses.\n')
  learned=self.call('finish',session=start['id'],name='Révision 学习')['result']
  self.assertEqual(learned['name'],'Révision 学习')
  rid=str(uuid.uuid4());run=self.call('run',id=learned['id'],request_id=rid)['result']
  self.assertIn('Gravity', (self.root/run['output']).read_text())
  before=self.calls.count('model');self.assertIn('error',self.call('run',id=learned['id'],request_id=rid));self.assertEqual(self.calls.count('model'),before)
  self.grants=[];self.assertIn('error',self.call('run',id=learned['id'],request_id=str(uuid.uuid4())))
 def test_image_conversion_and_pdf_page_operations(self):
  from PIL import Image
  from pypdf import PdfReader
  Image.new('RGB',(40,40),'red').save(self.root/'photo.png')
  converted=self.tool('convert_file',path='photo.png',to='pdf')
  self.assertIn('result',converted)
  self.assertEqual(len(PdfReader(self.root/'photo.pdf').pages),1)
  merged=self.tool('pdf_pages',action='merge',paths_json='["photo.pdf","photo.pdf"]',output='merged.pdf')
  self.assertIn('result',merged)
  self.assertEqual(len(PdfReader(self.root/'merged.pdf').pages),2)
 def test_unsafe_inputs_and_zip_are_rejected(self):
  import zipfile
  with zipfile.ZipFile(self.root/'bad.zip','w') as z:z.writestr('../escape','do not write')
  self.assertIn('error',self.tool('archive',action='extract',paths_json='["bad.zip"]'))
  self.assertFalse((self.root.parent/'escape').exists())
  self.assertIn('error',self.call('start',root=str(self.root),sources=['../outside'],output='example.md'))
if __name__=='__main__':unittest.main()
