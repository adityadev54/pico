"""Only the configured, server-verified Pico user may use the owner's model key."""
import hmac
import os
from .model_budget import BudgetDenied


def require_model_owner(owner):
    allowed = [item.strip() for item in os.environ.get('PICO_MODEL_OWNER_IDS', '').split(',') if item.strip()]
    if not isinstance(owner, str) or not any(hmac.compare_digest(owner, item) for item in allowed):
        raise BudgetDenied('AI planning is private to the configured owner account. Basic commands still work.')
