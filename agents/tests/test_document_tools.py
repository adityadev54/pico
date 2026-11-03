"""Real file conversions plus permission, source-change and original-preservation checks."""
import hashlib, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from pypdf import PdfReader, PdfWriter
from handlers import dispatch
from tools import TOOL_REGISTRY, ToolError
from native_search import NativeError
from task_execution import execute
from grant_sync import GrantFile

class DocumentToolsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.grants=[{'path':str(self.root),'access':'write'}]
  self.ctx={'grants':self.grants,'current_grants':lambda:self.grants}
  Image.new('RGB',(100,80),'white').save(self.root/'homework.jpg')
  for name in ('lecture.pdf','notes.pdf'):
   w=PdfWriter();w.add_blank_page(72,72);w.add_blank_page(72,72)
   with (self.root/name).open('wb') as f:w.write(f)
 def run_tool(self,name,args):return dispatch(name,TOOL_REGISTRY.validate(name,args),self.ctx)
 def test_photo_pdf_rotated_merged_split_are_real_and_sources_untouched(self):
  originals={p:p.read_bytes() for p in self.root.iterdir()}
  photo,evidence=self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  self.assertEqual(len(PdfReader(self.root/photo['path']).pages),1)
  self.assertEqual(photo['digest'],hashlib.sha256((self.root/photo['path']).read_bytes()).hexdigest())
  self.assertEqual(evidence['size_bytes'],photo['size_bytes'])
  merged,_=self.run_tool('pdf_pages',{'action':'merge','paths_json':json.dumps(['lecture.pdf','notes.pdf'])})
  self.assertEqual(len(PdfReader(self.root/merged['path']).pages),4)
  split,_=self.run_tool('pdf_pages',{'action':'split','paths_json':'["lecture.pdf"]','pages':'2'})
  self.assertEqual(len(PdfReader(self.root/split['path']).pages),1)
  rotated,_=self.run_tool('pdf_pages',{'action':'rotate','paths_json':'["notes.pdf"]','angle':'90'})
  self.assertEqual(PdfReader(self.root/rotated['path']).pages[0].rotation,90)
  for p,raw in originals.items():self.assertEqual(p.read_bytes(),raw)
 def test_pdf_text_to_docx_contains_actual_source_text(self):
  from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
  from docx import Document
  writer=PdfWriter();page=writer.add_blank_page(300,200)
  font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
  page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
  stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 100 Td (Photosynthesis uses light.) Tj ET');page[NameObject('/Contents')]=writer._add_object(stream)
  with (self.root/'reading.pdf').open('wb') as f:writer.write(f)
  result,_=self.run_tool('convert_file',{'path':'reading.pdf','to':'docx'})
  self.assertIn('Photosynthesis uses light.', '\n'.join(p.text for p in Document(self.root/result['path']).paragraphs))
 def test_watermark_output_is_readable_pdf(self):
  result,_=self.run_tool('pdf_pages',{'action':'watermark','paths_json':'["lecture.pdf"]','text':'Draft'})
  reader=PdfReader(self.root/result['path']);self.assertEqual(len(reader.pages),2)
  self.assertIn('Draft',reader.pages[0].extract_text())

 def test_repeat_does_not_overwrite(self):
  a,_=self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  b,_=self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  self.assertNotEqual(a['path'],b['path'])
 def test_revoked_or_downgraded_access_during_conversion_saves_nothing(self):
  import document_tools
  original=document_tools._convert_bytes
  for access in ('read',None):
   self.grants[:]=[{'path':str(self.root),'access':'write'}]
   def changed(*args):
    data=original(*args);self.grants[:]=[] if access is None else [{'path':str(self.root),'access':access}];return data
   with patch.object(document_tools,'_convert_bytes',changed),self.assertRaises(NativeError):self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
   self.assertFalse((self.root/'homework.pdf').exists())
 def test_source_change_and_cancellation_do_not_save(self):
  import document_tools
  original=document_tools._convert_bytes
  def changed(*args):
   data=original(*args);(self.root/'homework.jpg').write_bytes(b'new version');return data
  with patch.object(document_tools,'_convert_bytes',changed),self.assertRaises(NativeError):self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  Image.new('RGB',(20,20)).save(self.root/'homework.jpg')
  self.ctx['cancelled']=lambda:True
  with self.assertRaises(NativeError):self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  self.assertFalse((self.root/'homework.pdf').exists())
 def test_paths_and_scanned_text_fail_honestly(self):
  with self.assertRaises((NativeError,ToolError)):self.run_tool('convert_file',{'path':'../outside.jpg','to':'pdf'})
  with self.assertRaises((NativeError,ToolError)):self.run_tool('convert_file',{'path':'lecture.pdf','to':'txt'})
  self.assertFalse((self.root/'lecture.txt').exists())
 def test_race_at_atomic_create_cannot_replace_another_file(self):
  import os
  original=os.link
  def racing(source,target):
   Path(target).write_bytes(b'other writer wins')
   return original(source,target)
  with patch('os.link',racing),self.assertRaises(NativeError):self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  self.assertEqual((self.root/'homework.pdf').read_bytes(),b'other writer wins')

 def test_concurrent_output_is_preserved(self):
  import document_tools
  original=document_tools._convert_bytes
  def racing(*args):
   data=original(*args);(self.root/'homework.pdf').write_bytes(b'keep me');return data
  with patch.object(document_tools,'_convert_bytes',racing):result,_=self.run_tool('convert_file',{'path':'homework.jpg','to':'pdf'})
  self.assertEqual((self.root/'homework.pdf').read_bytes(),b'keep me');self.assertNotEqual(result['path'],'homework.pdf')

class GrantSyncTests(unittest.TestCase):
 def test_revocation_and_downgrade_win_and_stay_revoked_after_save(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'places.json';write=[{'path':root,'access':'write'}];read=[{'path':root,'access':'read'}]
   p.write_text(json.dumps({'grants':write}));tracker=GrantFile(p)
   p.write_text(json.dumps({'grants':read}));self.assertEqual(tracker.reconcile(write),read)
   p.write_text(json.dumps({'grants':[]}));self.assertEqual(tracker.reconcile(read),[])
   tracker.saved([]);self.assertEqual(tracker.reconcile([]),[])
 def test_ui_grant_survives_when_disk_is_unchanged(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'places.json';p.write_text('{"grants":[]}');tracker=GrantFile(p)
   grant=[{'path':root,'access':'read'}];self.assertEqual(tracker.reconcile(grant),grant)
