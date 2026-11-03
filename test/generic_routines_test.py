"""Different work types reuse the same learned file engine and output renderer."""
import json,tempfile,unittest
from pathlib import Path
from agents.skills.engine import SkillEngine
from agents.skills.contracts import validate_pack

class GenericRoutineTests(unittest.TestCase):
 def test_brief_checklist_and_meeting_summary_share_one_engine(self):
  for name,heading in [('Client brief','Audience'),('Release checklist','Before shipping'),('Meeting summary','Decisions')]:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    root=Path(d).resolve();(root/'Source.md').write_text('The team agreed to test the release on Friday.');calls=[]
    def model(body):
     calls.append(body)
     if body['operation']=='learn':return {'instructions':f'Prepare a {name} with a {heading} section.'}
     return {'title':name,'sections':[{'heading':heading,'items':[{'text':'Test the release on Friday.','source':'S1','quote':'test the release on Friday'}]}]}
    engine=SkillEngine(root/'recipes',lambda:[{'path':str(root),'access':'write'}],model)
    session=engine.start(root,['Source.md'],'Example.md');(root/'Example.md').write_text(f'# {name}\n## {heading}\nTest the release Friday.')
    routine=engine.finish(session['id'],name,True);result=engine.run(routine['id'],True)
    output=(root/result['output']).read_text();self.assertIn('## '+heading,output);self.assertNotIn('## Practice questions',output);self.assertEqual(len(calls),2)
 def test_unverified_claim_never_passes(self):
  with self.assertRaises(ValueError):validate_pack({'title':'Brief','sections':[{'heading':'Facts','items':[{'text':'Invented','source':'S1','quote':'not present'}]}]},[{'id':'S1','text':'actual source'}])
