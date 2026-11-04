import concurrent.futures,json,os,tempfile,unittest,uuid
from unittest.mock import patch,MagicMock
from relay.model_budget import ModelBudget,BudgetDenied
from relay.model_access import require_model_owner

class TrialTests(unittest.TestCase):
 def test_verified_account_required_and_no_redirect(self):
  owner=str(uuid.uuid4());response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'id':owner,'email_confirmed_at':'2026-11-04'}).encode()
  with patch.dict(os.environ,{'PICO_MODEL_PUBLIC_TRIAL':'1','PICO_MODEL_OWNER_IDS':'owner','SUPABASE_URL':'https://example.supabase.co','SUPABASE_SERVICE_ROLE_KEY':'not-real'}),patch('urllib.request.build_opener') as opener:
   opener.return_value.open.return_value=response
   require_model_owner(owner)
   response.__enter__.return_value.read.return_value=json.dumps({'id':owner}).encode()
   with self.assertRaises(BudgetDenied):require_model_owner(owner)
   with self.assertRaises(BudgetDenied):require_model_owner('')
 def test_trial_five_attempts_survive_restart_and_owner_ledger_separate(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1','PICO_TRIAL_TOTAL_USD':'5'}):
   for n in range(5):
    with patch('relay.model_budget.time.time',return_value=10000+n*61):
     b=ModelBudget(d+'/trial',trial=True);b.reserve('user',str(n));b.release(str(n))
   b=ModelBudget(d+'/trial',trial=True)
   self.assertEqual(b.remaining('user'),(0,True))
   with self.assertRaises(BudgetDenied):b.reserve('user','six')
   ModelBudget(d+'/owner').reserve('user','owner-request')
 def test_concurrent_same_account_admits_only_one(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}):
   b=ModelBudget(d+'/trial',trial=True)
   def reserve(n):
    try:b.reserve('user',str(n));return True
    except BudgetDenied:return False
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:self.assertEqual(sum(pool.map(reserve,range(8))),1)
 def test_shared_cap_cannot_be_exceeded_by_many_accounts(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1','PICO_TRIAL_TOTAL_USD':'0.2'}):
   b=ModelBudget(d+'/trial',trial=True)
   b.reserve('one','1');b.reserve('two','2')
   self.assertEqual(b.remaining('three'),(5,False))
   with self.assertRaises(BudgetDenied):b.reserve('three','3')
 def test_authorize_selects_trial_ledger(self):
  from server.model_safety import authorize,ENDPOINT,MODEL
  import urllib.request
  req=urllib.request.Request(ENDPOINT,data=json.dumps({'model':MODEL,'max_completion_tokens':400,'reasoning_effort':'minimal'}).encode())
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1','PICO_MODEL_LEDGER':d+'/owner','PICO_TRIAL_LEDGER':d+'/trial'}),patch('server.model_safety.require_model_owner'),patch('server.model_safety.is_trial',return_value=True):
   authorize(req,{'owner':'judge','id':'request'}, {})
   self.assertEqual(ModelBudget(d+'/trial',trial=True).remaining('judge')[0],4)
   self.assertEqual(ModelBudget(d+'/owner').remaining('judge')[0],5)

 def test_active_request_blocks_even_after_cooldown_until_finished(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}):
   b=ModelBudget(d+'/trial',trial=True)
   with patch('relay.model_budget.time.time',return_value=10000):b.reserve('one','first')
   with patch('relay.model_budget.time.time',return_value=10070):
    with self.assertRaises(BudgetDenied):b.reserve('one','second')
    b.release('first');b.reserve('one','second')
