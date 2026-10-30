import os,tempfile,unittest
from unittest.mock import patch
from relay.model_budget import ModelBudget,BudgetDenied
class BudgetTests(unittest.TestCase):
 def test_disabled_and_restart_and_no_retry(self):
  with tempfile.TemporaryDirectory() as d:
   b=ModelBudget(d+'/b.sqlite')
   with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'0'}):
    with self.assertRaises(BudgetDenied):b.reserve('u','1')
   with patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}):
    b.reserve('u','1')
    with self.assertRaises(BudgetDenied):ModelBudget(d+'/b.sqlite').reserve('u','1')
    b.reserve('v','2')
    with self.assertRaises(BudgetDenied):b.reserve('u','3')
 def test_global_daily_and_lifetime(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'PICO_MODEL_ENABLED':'1'}):
   b=ModelBudget(d+'/b.sqlite')
   for day in range(5):
    for n in range(10):
     with patch('relay.model_budget.time.time',return_value=86400*(day+1)+n*61):b.reserve('u',f'{day}:{n}')
    with patch('relay.model_budget.time.time',return_value=86400*(day+1)+1000):
     with self.assertRaises(BudgetDenied):b.reserve('v',f'overflow:{day}')
   with patch('relay.model_budget.time.time',return_value=86400*10):
    with self.assertRaises(BudgetDenied):ModelBudget(d+'/b.sqlite').reserve('u','lifetime')
