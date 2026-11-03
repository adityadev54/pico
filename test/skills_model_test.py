import io,json,unittest,uuid
from unittest.mock import patch
from server.skills.model import complete
from relay.service import ApiError
from relay.model_budget import BudgetDenied

class StudyModelTests(unittest.TestCase):
 def body(self):return {'operation':'learn','request_id':str(uuid.uuid4()),'sources':[{'id':'S1','name':'Lecture.md','text':'Cells have membranes.'}],'example':'# Recall\nWhat surrounds a cell? A membrane.'}
 def test_other_owner_never_loads_key_or_calls_network(self):
  with patch('server.skills.model.require_model_owner',side_effect=BudgetDenied('restricted')),patch('server.skills.model.muse_config') as config,patch('urllib.request.build_opener') as network:
   with self.assertRaises(ApiError) as e:complete('other',self.body())
   self.assertEqual(e.exception.status,403);config.assert_not_called();network.assert_not_called()
 def test_json_fence_is_supported_without_second_paid_call(self):
  response={'choices':[{'finish_reason':'stop','message':{'content':'```json\n{"instructions":"Two ideas, then recall questions."}\n```'}}]}
  with patch('server.skills.model.require_model_owner'),patch('server.skills.model.authorize'),patch('server.skills.model.muse_config',return_value={'url':'https://example.com','key':'test','model':'test'}),patch('urllib.request.build_opener') as opener:
   opener.return_value.open.return_value=io.BytesIO(json.dumps(response).encode())
   self.assertIn('instructions',complete('owner',self.body()));self.assertEqual(opener.return_value.open.call_count,1)
 def test_network_timeout_is_explicit_and_no_retry(self):
  with patch('server.skills.model.require_model_owner'),patch('server.skills.model.authorize'),patch('server.skills.model.muse_config',return_value={'url':'https://example.com','key':'test','model':'test'}),patch('urllib.request.build_opener') as opener:
   opener.return_value.open.side_effect=TimeoutError()
   with self.assertRaises(ApiError) as e:complete('owner',self.body())
   self.assertIn('time limit',e.exception.message);self.assertEqual(opener.return_value.open.call_count,1)

if __name__=='__main__':unittest.main()
