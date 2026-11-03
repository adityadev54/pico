import json,tempfile,unittest,uuid
from pathlib import Path
from agents.skills.engine import SkillEngine
from agents.skills.contracts import validate_pack

class TeachingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.notes=self.root/'Lecture.md';self.notes.write_text('Cells use membranes. Mitosis produces two cells.')
  self.grants=[{'path':str(self.root),'access':'write'}];self.calls=[]
  def model(body):
   self.calls.append(body)
   if body['operation']=='learn':return {'instructions':'Use two clear ideas and two short recall questions with answers.'}
   text=body['sources'][0]['text'];quote=text.split('.')[0]+'.'
   return {'title':'Study pack','ideas':[{'text':quote,'source':'S1','quote':quote} for _ in range(2)],'questions':[{'question':'What is the key idea?','answer':quote,'source':'S1','quote':quote} for _ in range(2)]}
  self.engine=SkillEngine(self.root/'recipes',lambda:self.grants,model)
 def teach(self):
  s=self.engine.start(self.root,['Lecture.md'],'Example.md')
  (self.root/'Example.md').write_text('# Cells\n## Ideas\n- Cell membranes\n## Recall\nWhat surrounds cells? Membranes.')
  return self.engine.finish(s['id'],'My study pack',True)
 def test_real_file_changes_and_fresh_inputs(self):
  recipe=self.teach();self.notes.write_text('Gravity attracts masses. Acceleration is a change in velocity.')
  result=self.engine.run(recipe['id'],True)
  output=self.root/result['output'];self.assertTrue(output.is_file());self.assertIn('Gravity',output.read_text());self.assertNotIn('Mitosis',output.read_text());self.assertEqual(result['bytes'],output.stat().st_size)
  self.assertEqual(self.calls[-1]['sources'][0]['text'],self.notes.read_text());self.assertTrue((self.root/'Example.md').exists())
 def test_must_observe_actual_edit(self):
  s=self.engine.start(self.root,['Lecture.md'],'Example.md')
  with self.assertRaisesRegex(ValueError,'No changed'):self.engine.finish(s['id'],'name',True)
  self.assertFalse(self.calls)
 def test_consent_revocation_duplicate(self):
  recipe=self.teach()
  with self.assertRaisesRegex(ValueError,'Approve'):self.engine.run(recipe['id'])
  rid=str(uuid.uuid4());self.engine.run(recipe['id'],True,rid)
  with self.assertRaisesRegex(ValueError,'already attempted'):self.engine.run(recipe['id'],True,rid)
  self.grants.clear()
  with self.assertRaisesRegex(ValueError,'write access'):self.engine.run(recipe['id'],True)
 def test_source_change_during_run_and_revocation(self):
  recipe=self.teach();original=self.engine.model
  def change(body):
   result=original(body);self.notes.write_text('Changed during the request.');return result
  self.engine.model=change
  with self.assertRaisesRegex(ValueError,'Inputs changed'):self.engine.run(recipe['id'],True)
  self.assertFalse(list(self.root.glob('study-pack-*.md')))
 def test_bad_citation_writes_nothing(self):
  recipe=self.teach();original=self.engine.model
  def bad(body):
   result=original(body);result['ideas'][0]['quote']='Invented evidence';return result
  self.engine.model=bad
  with self.assertRaisesRegex(ValueError,'citation'):self.engine.run(recipe['id'],True)
  self.assertFalse(list(self.root.glob('study-pack-*.md')))
 def test_traversal_and_symlink_escape(self):
  with self.assertRaises(ValueError):self.engine.start(self.root,['../outside.md'],'Example.md')
  (self.root/'escape.md').symlink_to('/etc/hosts')
  with self.assertRaises(ValueError):self.engine.start(self.root,['escape.md'],'Example.md')
 def test_failed_run_persisted_and_never_retried(self):
  recipe=self.teach();rid=str(uuid.uuid4())
  def fail(body):raise TimeoutError('Network timed out')
  self.engine.model=fail
  with self.assertRaises(TimeoutError):self.engine.run(recipe['id'],True,rid)
  saved=json.loads((self.engine.directory/(recipe['id']+'.json')).read_text());self.assertEqual(saved['runs'][-1]['status'],'failed')
  with self.assertRaisesRegex(ValueError,'already attempted'):self.engine.run(recipe['id'],True,rid)

if __name__=='__main__':unittest.main()

class ReuseTests(unittest.TestCase):
 setUp=TeachingTests.setUp
 teach=TeachingTests.teach
 def test_different_notes_keep_recipe_and_do_not_call_muse(self):
  recipe=self.teach();before=len(self.calls);(self.root/'Week2.md').write_text('Sound travels through matter.')
  self.engine.replace_sources(recipe['id'],['Week2.md'])
  saved=json.loads((self.engine.directory/(recipe['id']+'.json')).read_text());self.assertEqual(saved['instructions'],recipe['instructions']);self.assertEqual(saved['sources'],['Week2.md']);self.assertEqual(len(self.calls),before)
 def test_open_latest_checks_output_digest(self):
  recipe=self.teach();r=self.engine.run(recipe['id'],True);p=self.engine.latest(recipe['id']);self.assertEqual(p,self.root/r['output']);p.write_text('edited')
  with self.assertRaisesRegex(ValueError,'changed or moved'):self.engine.latest(recipe['id'])

class ControllerOutputTests(unittest.TestCase):
 def test_open_uses_only_verified_latest_file(self):
  from agents.skills.controller import SkillsController
  from unittest.mock import Mock,patch
  engine=Mock();engine.latest.return_value=Path('/tmp/verified-study-pack.md')
  controller=SkillsController(Mock());controller.engine=lambda:engine
  with patch('subprocess.Popen') as launch:
   controller.action({'choice':'open','id':'routine'})
   engine.latest.assert_called_once_with('routine');launch.assert_called_once_with(['/usr/bin/open','-e','/tmp/verified-study-pack.md'])
