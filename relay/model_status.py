"""Nonbillable provider reachability, cached for one minute. Never returns keys."""
import json,os,time,threading,urllib.request
from .model_access import require_model_owner, is_trial
from .model_budget import BudgetDenied
_cache={};_lock=threading.Lock()
def status(owner):
 try:require_model_owner(owner)
 except BudgetDenied:return {'state':'restricted','label':'Muse unavailable for this account'}
 if os.environ.get('PICO_MODEL_ENABLED')!='1':return {'state':'off','label':'Muse is off'}
 key=os.environ.get('MUSE_API_KEY','');model=os.environ.get('MUSE_MODEL','')
 if not key or not model:return {'state':'unavailable','label':'Muse is not configured'}
 with _lock:
  if time.time()-_cache.get('at',0)>60:
   try:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
     def redirect_request(self,*a,**kw):return None
    req=urllib.request.Request('https://api.meta.ai/v1/models',headers={'Authorization':'Bearer '+key})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=8) as response:data=json.load(response)
    ready=model in {m['id'] for m in data.get('data',[])}
   except Exception:ready=False
   _cache.update(at=time.time(),ready=ready)
  ready=_cache['ready']
 if is_trial(owner):
  from .model_budget import ModelBudget
  path=os.environ.get('PICO_TRIAL_LEDGER','')
  if not path or not os.path.isabs(path):return {'state':'unavailable','label':'Muse trial is not configured'}
  remaining,available=ModelBudget(path,trial=True).remaining(owner)
  if not remaining or not available:return {'state':'limited','label':'Muse trial used up; local features still work','remaining':remaining}
  return {'state':'ready' if ready else 'unavailable','label':f'Muse trial · {remaining} of 5 requests remaining' if ready else 'Muse unavailable','remaining':remaining}
 return {'state':'ready' if ready else 'unavailable','label':'Muse connected' if ready else 'Muse unavailable','checked_at':int(_cache['at']),'billable_check':False}
