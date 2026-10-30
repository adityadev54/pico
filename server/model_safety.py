"""Server-only Muse gate; no paid requests without explicit opt-in and ledger."""
import json
import os
from pathlib import Path
from relay.model_budget import ModelBudget,BudgetDenied
from relay.model_access import require_model_owner

ENDPOINT='https://api.meta.ai/v1/chat/completions'
MODEL='muse-spark-1.3'

def authorize(request, task, cfg):
    require_model_owner(task.get('owner'))
    if os.environ.get('PICO_MODEL_ENABLED')!='1':raise BudgetDenied('AI planning is off.')
    if request.full_url!=ENDPOINT:raise BudgetDenied('Use the approved Muse endpoint.')
    body=json.loads(request.data)
    if body.get('model')!=MODEL or body.get('max_completion_tokens')!=400 or body.get('reasoning_effort')!='minimal':raise BudgetDenied('Model request exceeds the test settings.')
    if len(request.data)>16000:raise BudgetDenied('Request too large for the AI test budget.')
    path=os.environ.get('PICO_MODEL_LEDGER','')
    if not path or not Path(path).is_absolute():raise BudgetDenied('A persistent model budget ledger is required.')
    ModelBudget(path).reserve(str(task.get('owner','local')),str(task['id']))
