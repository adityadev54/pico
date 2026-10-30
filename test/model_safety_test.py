import json,os,tempfile,unittest,uuid,urllib.request
from unittest.mock import patch
from server.agent.planner import plan
from server.model_safety import authorize,ENDPOINT
from relay.model_budget import BudgetDenied
class ModelSafetyTests(unittest.TestCase):
 def setUp(self):
  access=patch.dict(os.environ,{"PICO_MODEL_OWNER_IDS":"owner-1"});access.start();self.addCleanup(access.stop)
 def test_disabled_makes_no_network_call(self):
  with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'0'}),patch('urllib.request.urlopen') as network:
   response=plan({'id':'x','owner':'owner-1','input':'hello'},[],{'url':ENDPOINT,'key':'test-key'})
   self.assertIn('error',response);network.assert_not_called()
 def test_bad_endpoint_or_model_cannot_reserve_or_call(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1','PICO_MODEL_LEDGER':tmp+'/budget.sqlite'}):
   body={'model':'muse-wonder-1.0','max_completion_tokens':400,'reasoning_effort':'minimal'}
   request=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode())
   with self.assertRaises(BudgetDenied):authorize(request,{'id':'test','owner':'owner-1'}, {})
   self.assertFalse(os.path.exists(tmp+'/budget.sqlite'))
 def test_failed_request_is_not_retried_and_consumes_reservation(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1','PICO_MODEL_LEDGER':tmp+'/budget.sqlite'}),patch('urllib.request.urlopen',side_effect=OSError('offline')) as network:
   cfg={'url':ENDPOINT,'key':'test-key'};task={'id':str(uuid.uuid4()),'owner':'owner-1','input':'Open Calculator'}
   self.assertIn('error',plan(task,[],cfg));self.assertEqual(network.call_count,1)
   self.assertIn('error',plan(task,[],cfg));self.assertEqual(network.call_count,1)
