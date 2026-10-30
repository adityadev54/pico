import os,tempfile,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from relay.model_requests import create
from relay.service import ApiError,PicoService
from relay.state import RelayState
from relay.tests.fake import FakeSupabase
class ModelRequestTests(unittest.TestCase):
 def setUp(self):
  access=patch.dict(os.environ,{'PICO_MODEL_OWNER_IDS':'owner-1'});access.start();self.addCleanup(access.stop)
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.db=FakeSupabase();self.device={'id':str(uuid.uuid4()),'user_id':'owner-1','name':'Pico · Model test','os':'macos','last_seen':datetime.now(timezone.utc).isoformat(),'revoked_at':None}
  self.db.tables['devices'].append(self.device)
  self.service=PicoService(self.db,RelayState(Path(self.tmp.name)/'relay.sqlite'))
  self.body={'device_id':self.device['id'],'request_id':str(uuid.uuid4()),'text':'Bring up Calculator'}
 def test_offline_or_disabled_cannot_invoke_planner(self):
  with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'0'}),patch('server.agent.planner.plan') as model:
   with self.assertRaises(ApiError):create(self.service,'owner-1',self.body)
   model.assert_not_called()
  self.device['last_seen']='2000-01-01T00:00:00+00:00'
  with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}),patch('server.agent.planner.plan') as model:
   with self.assertRaises(ApiError):create(self.service,'owner-1',self.body)
   model.assert_not_called()
 def test_plan_uses_existing_owned_device_mailbox(self):
  reply={'tool_call':{'tool':'open_app','arguments':{'app':'Calculator'}}}
  with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}),patch('server.agent.planner.plan',return_value=reply) as model:
   task=create(self.service,'owner-1',self.body)['task']
   self.assertEqual(model.call_count,1);self.assertEqual(task['kind'],'open_app');self.assertEqual(task['result'],{});self.assertTrue(task['session_id']);self.assertEqual(self.db.tables['sessions'][0]['user_id'],'owner-1')
   mail=self.service.mailbox('owner-1',self.device['id'])
   self.assertEqual(mail[0]['payload']['app'],'Calculator');self.assertIn('expires_at',mail[0]['payload'])
 def test_model_cannot_plan_process_or_file_writes(self):
  with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}),patch('server.agent.planner.plan',return_value={'tool_call':{'tool':'process_run','arguments':{'argv_json':'[]'}}}):
   with self.assertRaises(ApiError):create(self.service,'owner-1',self.body)
   self.assertEqual(self.db.tables['tasks'],[])
