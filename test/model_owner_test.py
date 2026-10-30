import json,os,tempfile,unittest,uuid,urllib.request
from pathlib import Path
from unittest.mock import patch
from relay.model_requests import create
from relay.service import ApiError
from server.agent.planner import plan
from server.model_safety import ENDPOINT

class ModelOwnerTests(unittest.TestCase):
 def test_other_account_cannot_load_key_plan_or_use_budget(self):
  with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'PICO_MODEL_OWNER_IDS':'owner-1','PICO_MODEL_ENABLED':'1','PICO_MODEL_LEDGER':tmp+'/budget.sqlite'}),patch('server.config.muse_config') as config,patch('server.agent.planner.plan') as planner:
   with self.assertRaises(ApiError) as error:create(None,'teammate',{'owner':'owner-1'})
   self.assertEqual(error.exception.status,403)
   config.assert_not_called();planner.assert_not_called()
   self.assertFalse(Path(tmp+'/budget.sqlite').exists())
 def test_missing_owner_setting_fails_closed(self):
  with patch.dict(os.environ,{'PICO_MODEL_OWNER_IDS':''}),patch('server.config.muse_config') as config:
   with self.assertRaises(ApiError):create(None,'owner-1',{})
   config.assert_not_called()
 def test_planner_also_rejects_other_owner_without_paid_network(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'PICO_MODEL_OWNER_IDS':'owner-1','PICO_MODEL_ENABLED':'1','PICO_MODEL_LEDGER':tmp+'/budget.sqlite'}),patch('urllib.request.urlopen') as network:
   result=plan({'id':str(uuid.uuid4()),'owner':'teammate','input':'Open Calculator'},[],{'url':ENDPOINT,'key':'test-key'})
   self.assertIn('error',result);network.assert_not_called()
   self.assertFalse(Path(tmp+'/budget.sqlite').exists())

 def test_both_configured_accounts_share_access_but_others_do_not(self):
  from relay.model_access import require_model_owner
  from relay.model_budget import BudgetDenied
  with patch.dict(os.environ,{'PICO_MODEL_OWNER_IDS':'owner-1,owner-2'}):
   require_model_owner('owner-1');require_model_owner('owner-2')
   for value in ['owner-3',None,'', 'owner-1,owner-2']:
    with self.assertRaises(BudgetDenied):require_model_owner(value)
