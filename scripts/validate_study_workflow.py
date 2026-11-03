"""Real Muse smoke test using synthetic course notes; does not deploy code.
Requires the owner's existing Fly CLI login. Two bounded, budgeted requests.
"""
import json,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agents.skills.engine import SkillEngine

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--flyctl',required=True);args=p.parse_args()
 folder=ROOT/'.local/validation/study-workflow';folder.mkdir(parents=True,exist_ok=True)
 contracts=(ROOT/'agents/skills/contracts.py').read_text()
 model=(ROOT/'server/skills/model.py').read_text().replace('from relay.service','from server.relay.service').replace('from relay.model_budget','from server.relay.model_budget').replace('from agents.skills.contracts import validate_pack','').replace('from server.model_safety import authorize','')
 safety=(ROOT/'server/model_safety.py').read_text().replace('from relay.model_budget','from server.relay.model_budget').replace('from relay.model_access','from server.relay.model_access')
 calls=[]
 def remote(body):
  code='import os,json\nns={}\nexec('+repr(safety)+',ns)\nexec('+repr(contracts)+',ns)\nexec('+repr(model)+',ns)\nowner=os.environ["PICO_MODEL_OWNER_IDS"].split(",")[0].strip()\ntry:\n result=ns["complete"](owner,'+repr(body)+')\n print("PICO_RESULT="+json.dumps(result))\nexcept Exception as e:\n print("PICO_ERROR="+str(e))\n'
  result=subprocess.run([args.flyctl,'ssh','console','-a','pico-companion','-C','python -c '+shlex.quote(code)],capture_output=True,text=True,timeout=55)
  for line in result.stdout.splitlines():
   if line.startswith('PICO_RESULT='):
    value=json.loads(line.split('=',1)[1]);calls.append({'operation':body['operation'],'result':value});return value
   if line.startswith('PICO_ERROR='):raise RuntimeError(line)
  raise RuntimeError('Real Muse test did not return a result: '+result.stderr[-500:])
 notes=folder/'Lecture.md';notes.write_text('# Biology\nCells are surrounded by a selectively permeable membrane.\nMitosis produces two genetically identical daughter cells.\nMeiosis produces four genetically different gametes.\n')
 engine=SkillEngine(folder/'recipes',lambda:[{'path':str(folder),'access':'write'}],remote)
 (folder/'My study example.md').write_text('# Example to edit\n')
 session=engine.start(folder,['Lecture.md'],'My study example.md')
 (folder/'My study example.md').write_text('# Biology recall\n\n## Key ideas\n- A cell membrane controls what crosses it.\n- Mitosis makes two identical daughter cells.\n\n## Practice questions\n1. What surrounds a cell? A selectively permeable membrane.\n2. How many cells does mitosis produce? Two identical daughter cells.\n')
 recipe=engine.finish(session['id'],'Prepare my study material',True)
 notes.write_text('# Physics: motion\nVelocity is the rate of change of displacement.\nAcceleration is the rate of change of velocity.\nNewton\'s second law states that force equals mass times acceleration.\nThe SI unit of force is the newton.\n')
 result=engine.run(recipe['id'],True)
 output=folder/result['output'];text=output.read_text()
 assert 'mitosis' not in text.lower() and 'membrane' not in text.lower(),'Old topic leaked into repeat'
 report={'test':'Real Muse, observed file edit, changed lecture topic, fresh source quotes, verified output bytes','calls':calls,'result':result,'example_preserved':(folder/'My study example.md').is_file(),'provider_billing':'Unknown; two $0.10 conservative reservations under existing ledger'}
 (folder/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps({'output':str(output),'status':result['status'],'digest':result['digest']}))
if __name__=='__main__':main()
