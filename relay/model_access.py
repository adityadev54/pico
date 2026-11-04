"""Server-verified owner access or explicitly enabled verified-account trial."""
import hmac
import json
import os
import urllib.request
import uuid
from .model_budget import BudgetDenied


def is_trial(owner):
    allowed = [x.strip() for x in os.environ.get('PICO_MODEL_OWNER_IDS', '').split(',') if x.strip()]
    return not isinstance(owner, str) or not any(hmac.compare_digest(owner, x) for x in allowed)


def require_model_owner(owner):
    if not is_trial(owner):
        return
    if os.environ.get('PICO_MODEL_PUBLIC_TRIAL') != '1':
        raise BudgetDenied('AI planning is private to the configured owner account. Basic commands still work.')
    try:
        user_id = str(uuid.UUID(owner))
        url = os.environ['SUPABASE_URL'].rstrip('/') + '/auth/v1/admin/users/' + user_id
        key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
        request = urllib.request.Request(url, headers={'apikey': key, 'Authorization': 'Bearer ' + key})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
            user = json.load(response)
        if user.get('id') != user_id or not user.get('email_confirmed_at') or user.get('is_anonymous'):
            raise ValueError()
    except Exception:
        raise BudgetDenied('Verify your email and sign in to use the Muse trial. Basic commands still work.') from None
